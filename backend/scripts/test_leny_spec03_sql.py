"""Run existing-schema SQL tests only on the manifest-verified synthetic PG.

No migrations, application startup or external inference. The existing guarded
PowerShell launcher supplies ephemeral test credentials; never .env credentials.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

BACKEND=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BACKEND/'scripts'))


def child(output,continuity=False):
    from sqlalchemy import create_engine,event,text
    from sqlalchemy.engine import Engine,make_url
    import pytest
    manifest=json.loads(Path(os.environ['TEST_PG_MANIFEST']).read_text(encoding='utf-8-sig'))
    url=make_url(os.environ['TEST_MIGRATION_DATABASE_URL'])
    assert (url.host,url.port,url.database,url.username)==('127.0.0.1',55432,'bab_vdos_testing','bab_test_migrator')
    engine=create_engine(url,hide_parameters=True)
    with engine.connect() as db:
        assert db.scalar(text('SELECT instance_id FROM testing_control.instance'))==manifest['instance_id']
        assert Path(db.scalar(text('SHOW data_directory'))).resolve()==Path(manifest['data_directory']).resolve()
        assert db.scalar(text('SELECT version_num FROM alembic_version'))=='20261104_0023'
    engine.dispose()
    os.environ['TEST_PG_VALIDATED_INSTANCE']=manifest['instance_id']
    from app.services import seed_service
    from app.core.permissions import build_policy_lines
    def policy():
        assert (BACKEND/'app/security/policy.csv').read_text(encoding='utf-8')=='\n'.join(build_policy_lines())+'\n'
    policy();seed_service.sync_policy_file=policy
    violations=[]
    def forbid(_conn,_cursor,statement,*_):
        import re
        if re.search(r'\b(?:CREATE|ALTER|DROP|GRANT|REVOKE|TRUNCATE)\b',statement,re.I):
            violations.append('ddl');raise RuntimeError('DDL forbidden')
    event.listen(Engine,'before_cursor_execute',forbid)
    def audit(name,args):
        if name=='socket.connect':
            address=args[1]
            if not isinstance(address,tuple) or address[:2]!=('127.0.0.1',55432):
                violations.append('external');raise RuntimeError('External network forbidden')
        if name in {'subprocess.Popen','os.system'}:
            violations.append('process');raise RuntimeError('External process forbidden')
    sys.addaudithook(audit)
    targets=[str(BACKEND/'tests/integration/test_leny_spec03_scope.py'),str(BACKEND/'tests/integration/test_leny_original_features.py')]
    if continuity:targets.append(str(BACKEND/'tests/integration/test_leny_continuity_sql.py'))
    result=int(pytest.main(['-c',str(BACKEND.parent/'pytest.ini'),'--confcutdir',str(BACKEND/'tests'),
        '--basetemp',str(Path.cwd()/'pytest-temp'),'-q','-p','no:cacheprovider','--junitxml='+output,
        *targets]))
    return result or bool(violations)


if __name__=='__main__':
    if len(sys.argv)>2 and sys.argv[1]=='--child':raise SystemExit(child(sys.argv[2],len(sys.argv)>3 and sys.argv[3]=='continuity'))
    from run_base_tests import _child_environment
    output=str(Path(sys.argv[1]).resolve())
    with TemporaryDirectory(prefix='bab-leny-spec03-sql-') as temp:
        environment=_child_environment(temp)
        for key in ('TEST_PG_MANIFEST','TEST_DATABASE_URL','TEST_MIGRATION_DATABASE_URL'):
            environment[key]=os.environ[key]
        environment.update(ENVIRONMENT='test',DATABASE_URL=environment['TEST_DATABASE_URL'],LENY_RUNTIME_AUTOSTART='false')
        raise SystemExit(subprocess.call([sys.executable,'-B',__file__,'--child',output,*sys.argv[2:]],cwd=temp,env=environment))
