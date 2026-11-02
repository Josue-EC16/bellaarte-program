"""Real local decoders/Windows limits, synthetic fixtures, no PostgreSQL or SMTP."""
import os
from pathlib import Path
import runpy
import subprocess
import sys
from tempfile import TemporaryDirectory

BACKEND = Path(__file__).resolve().parents[1]


def child():
    import psycopg2
    import pytest
    import smtplib
    from sqlalchemy import event
    from sqlalchemy.engine import Engine
    violations = []

    def forbidden(*_args, **_kwargs):
        violations.append('external operation')
        raise RuntimeError('Parser test blocked an external operation')
    psycopg2.connect = forbidden
    event.listen(Engine, 'do_connect', forbidden)
    smtplib.SMTP = smtplib.SMTP_SSL = forbidden
    allowed = str(BACKEND/'scripts/validate_leny_document.py')

    def guard(name, arguments):
        if name == 'socket.connect':
            forbidden()
        if name == 'subprocess.Popen':
            executable, args, cwd, environment = arguments
            expected = [sys.executable,'-B','-I',allowed]
            if (executable not in (None, sys.executable) or args not in (expected, subprocess.list2cmdline(expected))
                    or not Path(cwd).resolve().is_relative_to(Path.cwd().resolve())
                    or any(key.startswith(('DB_', 'DATABASE_', 'SMTP_', 'JWT_')) for key in environment)):
                forbidden()
        elif name in {'os.system','os.exec','os.posix_spawn'}:
            forbidden()
    sys.addaudithook(guard)
    os.environ['LENY_PARSER_NATIVE_TESTS'] = '1'
    result = pytest.main(['-q','-p','no:cacheprovider', '--confcutdir',str(BACKEND/'tests'),
                         '--basetemp',str(Path.cwd()/'pytest-parser'),str(BACKEND/'tests/test_leny_document_parsers.py')])
    return 1 if violations else int(result)


def main():
    from run_base_tests import _child_environment
    with TemporaryDirectory(prefix='bab-leny-native-parsers-') as temporary:
        environment = _child_environment(temporary)
        bootstrap = "import runpy,sys; r=runpy.run_path(sys.argv[1]); raise SystemExit(r['child']())"
        return subprocess.run([sys.executable,'-B','-c',bootstrap,str(Path(__file__).resolve())],cwd=temporary,env=environment).returncode


if __name__ == '__main__':
    raise SystemExit(main())
