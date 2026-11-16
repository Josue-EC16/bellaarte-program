"""Private source checkpoint and inverse patch; never copies the real .env."""
from datetime import datetime,timezone
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from run_leny_spec03_review import root_path,prepare,save,BACKEND

ROOT=BACKEND.parent


def main():
    review=root_path();prepare(review);checkpoint=review.parent
    paths=set((ROOT/'backend/app/services').glob('leny*.py'))
    # Include the actual locally modified application/test dependencies, not just
    # HEAD or this feature's files. This is a non-executable source backup:
    # no .env, venv, uploads, documents, database or node_modules are copied.
    for directory in ('backend/app','backend/tests','backend/scripts','backend/alembic','frontend/src'):
        paths.update(path for path in (ROOT/directory).rglob('*')
            if path.suffix in {'.py','.ps1','.jsx','.js','.css','.json','.toml','.ini','.conf','.csv'}
            and '__pycache__' not in path.parts)
    paths.update(ROOT/name for name in ('backend/requirements.txt','frontend/package.json','frontend/pnpm-lock.yaml',
        'pytest.ini','backend/main.py','backend/alembic.ini'))
    paths.update((ROOT/'frontend/src/pages/leny').rglob('*'))
    paths.update((ROOT/'backend/scripts').glob('*leny*spec03*'))
    paths.update((ROOT/'backend/tests').glob('test_leny_spec03*.py'))
    paths.update(ROOT/name for name in (
        'backend/app/core/config.py','backend/app/api/routers/leny.py','backend/app/models/leny.py',
        'backend/app/schemas/leny.py','backend/.env.example',
        'backend/alembic/versions/20261105_0025_leny_quality_profile.py',
        'backend/tests/fixtures/leny_spec03_development.json','backend/tests/integration/test_leny_spec03_scope.py'))
    snapshot=checkpoint/('candidate-source-'+datetime.now(timezone.utc).strftime('%H%M%S'))
    snapshot.mkdir()
    hashes={};inverse=[];changes=[]
    for path in sorted(paths):
        if not path.is_file() or path.name=='.env' or '__pycache__' in path.parts:continue
        relative=path.relative_to(ROOT).as_posix();data=path.read_bytes()
        destination=snapshot/relative;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,destination)
        hashes[relative]=hashlib.sha256(data).hexdigest()
        before=checkpoint/'source-before'/relative
        if before.is_file() and before.read_bytes()!=data:
            old=before.read_text(encoding='utf-8-sig');new=data.decode('utf-8-sig')
            inverse.extend(difflib.unified_diff(new.splitlines(keepends=True),old.splitlines(keepends=True),
                fromfile='a/'+relative,tofile='b/'+relative))
            changes.append(dict(path=relative,before_sha256=hashlib.sha256(before.read_bytes()).hexdigest(),after_sha256=hashes[relative]))
    (snapshot/'inverse-existing-files.patch').write_text(''.join(inverse),encoding='utf-8')
    save(snapshot/'changed-existing-files.json',changes)
    public=dict(head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        at=datetime.now(timezone.utc).isoformat(),files=hashes,global_profile='baseline',
        corpus_manifest_sha256=hashlib.sha256((checkpoint/'external-corpus.json').read_bytes()).hexdigest(),
        real_env_copied=False,human_acceptance=None)
    save(ROOT/'documentacion/evidencias/leny_spec03_candidate_manifest.json',public)
    save(checkpoint/'candidate-snapshot.json',dict(path=str(snapshot),files=len(hashes),changed_existing=len(changes)))
    print('Candidate source checkpoint:',len(hashes),'files; no real .env copied.')


if __name__=='__main__':main()
