"""Run contract/helper tests without application credentials or external services.

From backend: python -B scripts/run_base_tests.py [tests/test_file.py[::test_name]]
This runner is for the base suite, not PostgreSQL integration tests.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory


BACKEND_DIR = Path(__file__).resolve().parents[1]
TESTS_DIR = BACKEND_DIR / "tests"
INTEGRATION_DIR = TESTS_DIR / "integration"


def _test_targets(targets: list[str]) -> list[str]:
    result = []
    for target in targets or [str(TESTS_DIR)]:
        path_text, *nodes = target.split("::")
        path = Path(path_text)
        if not path.is_absolute():
            path = BACKEND_DIR / path
        path = path.resolve()
        if not path.is_relative_to(TESTS_DIR.resolve()):
            raise ValueError("Test selection must stay inside backend/tests.")
        if path.is_relative_to(INTEGRATION_DIR.resolve()):
            raise ValueError("PostgreSQL integration tests require the isolated integration runner.")
        if not path.exists() or (path.is_file() and path.suffix != ".py"):
            raise ValueError("Select an existing test directory or Python test file.")
        if any(not node for node in nodes):
            raise ValueError("Empty test node identifiers are not allowed.")
        result.append("::".join([str(path), *nodes]))
    return result


def _child_environment(temporary_dir: str) -> dict[str, str]:
    # Allowlist OS/runtime locations; never inherit DATABASE_URL, DB_*, SMTP_*,
    # PYTEST_ADDOPTS, plugin configuration, or application secrets.
    allowed = {
        "SYSTEMROOT", "WINDIR", "SYSTEMDRIVE", "COMSPEC", "PATH", "PATHEXT",
        "USERPROFILE", "HOMEDRIVE", "HOMEPATH", "APPDATA", "LOCALAPPDATA",
        "PROGRAMFILES", "PROGRAMFILES(X86)", "PROGRAMDATA", "ALLUSERSPROFILE",
    }
    environment = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    environment.update({
        "TEMP": temporary_dir,
        "TMP": temporary_dir,
        "TMPDIR": temporary_dir,
        "PYTHONPATH": str(BACKEND_DIR),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONUTF8": "1",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "ENVIRONMENT": "test",
        "DATABASE_URL": "postgresql+psycopg2://base_tests:synthetic@127.0.0.1:1/bab_vdos_base_tests",
        "JWT_SECRET_KEY": "base-suite-only-access-key-no-business-access",
        "JWT_REFRESH_SECRET_KEY": "base-suite-only-refresh-key-no-business-access",
        "BACKUP_DIR": str(Path(temporary_dir) / "backups"),
        "SMTP_SERVER": "smtp.invalid",
        "SMTP_USERNAME": "",
        "SMTP_PASSWORD": "",
    })
    return environment


def _run_child(targets: list[str]) -> int:
    # These guards are installed before importing any application module or
    # collecting tests. Record attempts even if application code catches them.
    import smtplib

    import psycopg2
    import pytest
    from sqlalchemy import event
    from sqlalchemy.engine import Engine

    violations: list[str] = []

    def deny(operation: str):
        def blocked(*_args, **_kwargs):
            violations.append(operation)
            raise RuntimeError(f"Base suite blocked external operation: {operation}.")

        return blocked

    psycopg2.connect = deny("PostgreSQL connection")
    event.listen(Engine, "do_connect", deny("SQLAlchemy connection"))
    smtplib.SMTP = deny("SMTP connection")
    smtplib.SMTP_SSL = deny("SMTP SSL connection")

    def prevent_processes(event_name: str, _arguments: tuple) -> None:
        if event_name in {"subprocess.Popen", "os.system", "os.posix_spawn", "os.exec"}:
            deny("external process")()

    # Backup tests replace subprocess.run with an in-process fake; those mocks
    # continue working. A real pg_dump (or other child process) cannot start.
    sys.addaudithook(prevent_processes)

    from app.core.permissions import build_policy_lines
    from app.services import seed_service

    def verify_policy_only() -> None:
        policy_path = BACKEND_DIR / "app" / "security" / "policy.csv"
        expected = "\n".join(build_policy_lines()) + "\n"
        if not policy_path.is_file() or policy_path.read_text(encoding="utf-8") != expected:
            raise RuntimeError("Casbin policy drift detected; base suite will not rewrite policy.csv.")

    seed_service.sync_policy_file = verify_policy_only
    verify_policy_only()

    class ExternalEffectsGuard:
        @pytest.hookimpl(trylast=True)
        def pytest_sessionfinish(self, session, exitstatus):
            if violations:
                session.exitstatus = pytest.ExitCode.TESTS_FAILED
                reporter = session.config.pluginmanager.get_plugin("terminalreporter")
                if reporter is not None:
                    reporter.write_sep("!", "Blocked external operations: " + ", ".join(sorted(set(violations))))

    return int(pytest.main([
        "-c", str(BACKEND_DIR.parent / "pytest.ini"),
        "--confcutdir", str(TESTS_DIR),
        "--ignore", str(INTEGRATION_DIR),
        "--basetemp", str(Path.cwd() / "pytest-tmp"),
        "-q", "-p", "no:cacheprovider",
        *_test_targets(targets),
    ], plugins=[ExternalEffectsGuard()]))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tests", nargs="*", help="Test paths relative to backend, optionally with ::node identifiers.")
    arguments = parser.parse_args()
    try:
        targets = _test_targets(arguments.tests)
    except ValueError as error:
        parser.error(str(error))

    with TemporaryDirectory(prefix="bab-vdos-base-tests-") as temporary_dir:
        # run_path avoids a public child-mode switch that could skip setup.
        bootstrap = (
            "import runpy, sys; "
            "runner = runpy.run_path(sys.argv[1]); "
            "raise SystemExit(runner['_run_child'](sys.argv[2:]))"
        )
        completed = subprocess.run(
            [sys.executable, "-B", "-c", bootstrap, str(Path(__file__).resolve()), *targets],
            cwd=temporary_dir,
            env=_child_environment(temporary_dir),
            check=False,
        )
        return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
