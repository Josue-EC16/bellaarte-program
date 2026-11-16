"""Real multipart/JWT HTTP smoke against disposable ERP8001 only; no DB access."""
import hashlib
import io
import json
import os
from pathlib import Path
import re
from uuid import uuid4
import zipfile

import httpx


def main():
    username, password=os.environ.get('LENY_SMOKE_USERNAME',''),os.environ.get('LENY_SMOKE_PASSWORD','')
    if not re.fullmatch(r'leny_smoke_[a-f0-9]{12}',username) or not password:
        raise RuntimeError('Disposable isolated smoke identity required')
    from pypdf import PdfWriter
    import pyvips
    pdf=io.BytesIO();writer=PdfWriter();writer.add_blank_page(width=100,height=100);writer.write(pdf)
    docx=io.BytesIO()
    with zipfile.ZipFile(docx,'w') as archive:
        archive.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        archive.writestr('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        archive.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Procedimiento sintético: revisar las entradas del inventario.</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>Control diario</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>')
    image=pyvips.Image.black(40,30)
    fixtures=[('manual-http.pdf',pdf.getvalue()),('procedimiento-http.docx',docx.getvalue()),('imagen-http.jpg',image.jpegsave_buffer()),('imagen-http.png',image.pngsave_buffer())]
    results={}
    with httpx.Client(base_url='http://127.0.0.1:8001/api/v1',trust_env=False,timeout=45) as client:
        assert client.get('/leny/documents').status_code==401
        results['anonymous_401']=True
        response=client.post('/auth/login',json={'username':username,'password':password});response.raise_for_status()
        client.headers['Authorization']='Bearer '+response.json()['access_token']
        folders=client.get('/leny/documents/folders');folders.raise_for_status()
        folder=next((f for f in folders.json()['items'] if f['name']=='QA Biblioteca de prueba'),None)
        if folder is None:
            created=client.post('/leny/documents/folders',json={'name':'QA Biblioteca de prueba','role_codes':['ADMIN']});created.raise_for_status()
            folder=next(f for f in created.json()['items'] if f['name']=='QA Biblioteca de prueba')
        documents=[]
        first_metadata=None
        for name,content in fixtures:
            metadata={'request_id':str(uuid4()),'sha256':hashlib.sha256(content).hexdigest(),'folder_id':folder['id'],'title':name,'description':'Archivo sintético de prueba'}
            reply=client.post('/leny/documents',files=[('metadata',(None,json.dumps(metadata),'application/json')),('file',(name,content,'application/octet-stream'))])
            if reply.status_code!=200:
                raise RuntimeError('Upload failed safely: '+str(reply.status_code)+' '+str(reply.json().get('detail',{}).get('code','')))
            document=reply.json();documents.append(document)
            assert document['status']=='pending_contextualization' and document['published_version_id'] is None
            assert document['role_codes']==['ADMIN']
            version=document['versions'][0]
            content_response=client.get(f"/leny/documents/{document['id']}/versions/{version['id']}/content")
            assert content_response.content==content and 'attachment' in content_response.headers['content-disposition']
            assert content_response.headers['cache-control']=='no-store' and content_response.headers['x-content-type-options']=='nosniff'
            if first_metadata is None:first_metadata=metadata
        results['four_real_multipart_uploads_original_hashes_and_private_headers']=True
        first=documents[0]
        metadata={'request_id':str(uuid4()),'sha256':hashlib.sha256(pdf.getvalue()).hexdigest(),'revision':first['revision']}
        version_reply=client.post(f"/leny/documents/{first['id']}/versions",files=[('metadata',(None,json.dumps(metadata))),('file',('new-version.pdf',pdf.getvalue(),'application/pdf'))]);version_reply.raise_for_status()
        assert [v['number'] for v in version_reply.json()['versions']]==[2,1]
        results['version_two_preserves_previous']=True
        duplicate=client.post('/leny/documents',files=[('metadata',(None,json.dumps(first_metadata))),('file',(fixtures[0][0],fixtures[0][1],'application/pdf'))]);duplicate.raise_for_status()
        assert duplicate.json()['id']==first['id'] and duplicate.json()['version_count']==2
        results['duplicate_after_quota_not_recharged']=True
        exceeded=client.post('/leny/documents',files=[('metadata',(None,json.dumps({**first_metadata,'request_id':str(uuid4())}))),('file',('again.pdf',pdf.getvalue()))])
        assert exceeded.status_code==429 and int(exceeded.headers['retry-after'])>0
        results['sixth_generation_429']=True
        docx_item=documents[1]
        preview=client.get(f"/leny/documents/{docx_item['id']}/versions/{docx_item['versions'][0]['id']}/preview");preview.raise_for_status()
        assert preview.json()['kind']=='docx' and preview.json()['blocks'][1]['rows']==[['Control diario']]
        results['real_docx_paragraph_and_table_preview']=True
        for image_doc in documents[2:]:
            preview=client.get(f"/leny/documents/{image_doc['id']}/versions/{image_doc['versions'][0]['id']}/preview");preview.raise_for_status()
            assert preview.headers['content-type']=='image/png' and preview.content.startswith(b'\x89PNG')
        results['real_image_previews']=True
        assert client.post(f"/leny/documents/{first['id']}/publish").status_code==409
        assert client.get(f"/leny/documents/{first['id']}/versions/{docx_item['versions'][0]['id']}/content").status_code==404
        assert client.get('/leny/documents/'+str(uuid4())).status_code==404
        results['publish_blocked_and_foreign_version_404']=True
        current=version_reply.json()
        trashed=client.delete(f"/leny/documents/{first['id']}",params={'revision':current['revision']});trashed.raise_for_status()
        assert trashed.json()['state']=='trash'
        assert client.get(f"/leny/documents/{first['id']}/versions/{first['versions'][0]['id']}/content").status_code==409
        change={'revision':trashed.json()['revision'],'folder_id':folder['id'],'role_codes':['ADMIN']}
        confirmation=client.post(f"/leny/documents/{first['id']}/change-preview",json=change);confirmation.raise_for_status()
        restored=client.post(f"/leny/documents/{first['id']}/restore",json={**change,'confirmation':confirmation.json()['token']});restored.raise_for_status()
        assert restored.json()['state']=='active' and restored.json()['role_codes']==['ADMIN']
        results['trash_blocks_content_and_confirmed_restore']=True
        client.headers.pop('Authorization')
        refreshed=client.post('/auth/refresh');refreshed.raise_for_status()
        client.headers['Authorization']='Bearer '+refreshed.json()['access_token']
        assert client.get('/leny/documents').status_code==200
        results['jwt_refresh_preserves_library_access']=True
    report={'scope':'real HTTP localhost8001, native parsers, JWT, disposable person and storage; no business database','results':results}
    path=Path(__file__).resolve().parents[2]/'documentacion/evidencias/leny_rag01_http.json'
    path.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__':
    try:
        main()
    except Exception as error:
        import traceback
        location=next((frame.lineno for frame in reversed(traceback.extract_tb(error.__traceback__)) if frame.filename==__file__),0)
        print('Document HTTP smoke failed: '+type(error).__name__+' line='+str(location))
        if isinstance(error,httpx.HTTPStatusError):
            print('HTTP status:',error.response.status_code, 'path:',error.request.url.path)
            try:
                detail=error.response.json().get('detail',{})
                print('reason code:',detail.get('code','') if isinstance(detail,dict) else 'request rejected')
            except ValueError:
                pass
        if isinstance(error,RuntimeError):print(str(error))
        raise SystemExit(1) from None
