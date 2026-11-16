"""Reproduce offline LENY regression with sanitized configuration and guards."""
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from run_base_tests import _child_environment

ROOT=Path(__file__).resolve().parents[2]
BACKEND=ROOT/'backend'


def main(continuity=False):
    prefix='leny_spec031' if continuity else 'leny_spec03'
    files=[str(path.resolve()) for path in (BACKEND/'tests').glob('test_leny*.py')]
    node=str(BACKEND/'tests/test_leny_gemini_preparation.py')+'::test_default_service_import_does_not_import_google_or_open_network'
    bootstrap=("import sys,runpy,pytest; original=pytest.main; "
        "pytest.main=lambda args,**kw: original(args+['--junitxml='+sys.argv[2],'-k','not test_default_service_import_does_not_import_google_or_open_network'],**kw); "
        "m=runpy.run_path(sys.argv[1]); raise SystemExit(m['_run_child'](sys.argv[4:]))")
    with TemporaryDirectory(prefix='bab-spec03-regression-') as temporary:
        environment=_child_environment(temporary)
        result=subprocess.call([sys.executable,'-B','-c',bootstrap,str(BACKEND/'scripts/run_base_tests.py'),
            str(ROOT/('documentacion/evidencias/'+prefix+'_regression_final.xml')),node,*files],cwd=temporary,env=environment)
        if result:return result
        # This inspected import test starts a Python child and installs its own
        # socket/import guards; the other tests retain the process prohibition.
        return subprocess.call([sys.executable,'-B','-m','pytest','-c',str(ROOT/'pytest.ini'),
            '--confcutdir',str(BACKEND/'tests'),'-q','-p','no:cacheprovider','--basetemp',str(Path(temporary)/'import-test'),
            '--junitxml='+str(ROOT/('documentacion/evidencias/'+prefix+'_import_test.xml')),node],cwd=temporary,env=environment)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--continuity',action='store_true')
    raise SystemExit(main(parser.parse_args().continuity))
