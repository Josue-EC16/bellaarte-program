"""Offline validator replay; never a new generation or end-to-end result."""
import json
from pathlib import Path
import sys

BACKEND=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BACKEND))
sys.path.insert(0,str(BACKEND/'scripts'))


def replay(root):
    from app.services.leny_spec03_synthesis import validate
    from app.services.leny_rag_synthesis import failure_kind
    from run_leny_spec03_review import save
    job=json.loads((root/'results/C1-Gemini-spec03.json').read_text(encoding='utf-8'))
    public=[];private=[]
    for case in job['cases']:
        path=root/'traces'/('trace-'+case['request_id']+'.json')
        if not path.exists():continue
        trace=json.loads(path.read_text(encoding='utf-8'))
        if trace.get('prompt',{}).get('protocol')!='spec03-atomic-v1':continue
        raw=trace.get('generation',{}).get('raw')
        if not raw:continue
        rows=trace.get('packed_evidence',{}).get('rows',[])
        verdict=trace.get('packed_evidence',{}).get('verdict','none')
        record=dict(case=case['id'],before=trace.get('validation'),generated_again=False)
        try:
            answer=validate(raw,rows,allow_general=not rows,verdict=verdict)
            record.update(after='accepted',scope=answer.response_scope)
            private.append(record|dict(response=str(answer),sources=rows))
        except (ValueError,TypeError,KeyError) as error:
            record.update(after='rejected',reason=failure_kind(error))
        public.append(record)
    save(root/'offline-validator-replay.json',private)
    save(BACKEND.parent/'documentacion/evidencias/leny_spec03_validator_replay.json',
        dict(scope='offline_fixed_generation_validator_only',cases=public,semantic_acceptance=None))
    print('Offline validator replay cases:',len(public),'No new generation or acceptance claimed.')


if __name__=='__main__':
    from run_leny_spec03_review import root_path,prepare
    root=root_path();prepare(root);replay(root)
