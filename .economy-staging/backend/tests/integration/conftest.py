"""Fail-closed PostgreSQL fixtures. Never load application settings at collection.

Only the separately authorized integration launcher may supply the manifest and
both explicit URLs. No fallback to DATABASE_URL, .env, or the business database.
"""

import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _configuration():
    if os.environ.get("ENVIRONMENT") != "test":
        raise pytest.UsageError("Integration requires the sanitized testing launcher.")
    if Path.cwd().resolve().is_relative_to(PROJECT_ROOT) or (Path.cwd() / ".env").exists():
        raise pytest.UsageError("Integration must start from an owned temporary directory without .env.")
    manifest_path = os.environ.get("TEST_PG_MANIFEST")
    if not manifest_path or not Path(manifest_path).is_absolute():
        raise pytest.UsageError("TEST_PG_MANIFEST must explicitly name an absolute manifest path.")
    try:
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8-sig"))
        UUID(manifest["instance_id"])
        assert manifest["host"] == "127.0.0.1" and manifest["port"] == 55432
        assert manifest["database"] == "bab_vdos_testing"
        assert manifest["test_role"] == "bab_test_runner"
        assert manifest["migration_role"] == "bab_test_migrator"
        assert Path(manifest["data_directory"]).is_absolute()
        assert not Path(manifest["data_directory"]).resolve().is_relative_to(PROJECT_ROOT)
    except (OSError, KeyError, ValueError, AssertionError, TypeError):
        raise pytest.UsageError("Invalid or unsafe PostgreSQL testing manifest.") from None

    urls = {}
    for variable, role in (("TEST_DATABASE_URL", "test_role"), ("TEST_MIGRATION_DATABASE_URL", "migration_role")):
        try:
            supplied = os.environ[variable]
            url = make_url(supplied)
            assert url.drivername in {"postgresql", "postgresql+psycopg2"}
            assert (url.host, url.port, url.database, url.username) == (
                manifest["host"], manifest["port"], manifest["database"], manifest[role])
            assert url.password and not url.query
        except (KeyError, ValueError, AssertionError):
            raise pytest.UsageError("Explicit testing URLs must match the provisioned host, port, database and roles.") from None
        urls[variable] = url
    if os.environ.get("DATABASE_URL") != os.environ["TEST_DATABASE_URL"]:
        raise pytest.UsageError("Application URL must explicitly equal the validated testing URL.")
    if any(name.startswith("DB_") for name in os.environ):
        raise pytest.UsageError("Inherited DB_* variables are forbidden in integration.")
    config_module = sys.modules.get("app.core.config")
    database_module = sys.modules.get("app.core.database")
    if config_module is not None or database_module is not None:
        settings = getattr(config_module, "settings", None)
        if (os.environ.get("TEST_PG_VALIDATED_INSTANCE") != manifest["instance_id"]
                or settings is None or settings.effective_database_url != os.environ["TEST_DATABASE_URL"]):
            raise pytest.UsageError("Preloaded application settings were not validated by the integration launcher.")
        if database_module is not None and database_module.engine.url != urls["TEST_DATABASE_URL"]:
            raise pytest.UsageError("The preloaded application engine differs from the validated testing URL.")
    return manifest, urls


def assert_identity(connection, manifest, *, migrator=False):
    row = connection.execute(text("SELECT current_database(), current_user, inet_server_port(), current_setting('server_version_num')::integer")).one()
    expected_role = manifest["migration_role"] if migrator else manifest["test_role"]
    if tuple(row[:3]) != (manifest["database"], expected_role, manifest["port"]) or row[3] < 170000:
        raise pytest.UsageError("Connected server identity differs from the authorized test cluster.")
    identities = connection.execute(text("SELECT instance_id FROM testing_control.instance")).scalars().all()
    if identities != [manifest["instance_id"]]:
        raise pytest.UsageError("The isolated cluster provisioning badge is absent or different.")
    if migrator:
        directory = connection.execute(text("SHOW data_directory")).scalar_one()
        if os.path.normcase(str(Path(directory).resolve())) != os.path.normcase(str(Path(manifest["data_directory"]).resolve())):
            raise pytest.UsageError("The server data directory differs from the authorized manifest.")


@pytest.fixture(scope="session")
def pg_cluster():
    manifest, urls = _configuration()
    engines = {}
    try:
        for variable, url in urls.items():
            engine = create_engine(url, connect_args={"connect_timeout": 5, "options": "-c lock_timeout=5000 -c statement_timeout=15000"})
            engines[variable] = engine
            with engine.connect() as connection:
                assert_identity(connection, manifest, migrator=variable == "TEST_MIGRATION_DATABASE_URL")
                if connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() != "20261018_0016":
                    raise pytest.UsageError("Integration requires the reviewed Alembic head, never create_all.")
        yield SimpleNamespace(engine=engines["TEST_DATABASE_URL"], migration_engine=engines["TEST_MIGRATION_DATABASE_URL"],
                              manifest=manifest, assert_identity=assert_identity)
    except SQLAlchemyError:
        raise pytest.UsageError("Could not verify the explicitly provisioned testing PostgreSQL; no fallback is allowed.") from None
    finally:
        for engine in engines.values():
            engine.dispose()


@pytest.fixture
def synthetic_recipient(pg_cluster):
    """Committed synthetic IDs allow independent connections; cleanup is PK scoped."""
    token = uuid4().hex
    with pg_cluster.engine.begin() as connection:
        assert_identity(connection, pg_cluster.manifest)
        role_id = connection.execute(text("INSERT INTO roles (codigo,nombre,activo) VALUES (:code,:name,true) RETURNING id"),
                                     {"code": "QA_" + token[:20], "name": "QA " + token}).scalar_one()
        user_id = connection.execute(text("""
            INSERT INTO usuarios (nombres,apellido_paterno,ci,celular,correo,zona,activo)
            VALUES ('QA','SINTETICO',:ci,'00000000',:mail,'TEST',true) RETURNING id
        """), {"ci": token[:25], "mail": token + "@example.invalid"}).scalar_one()
        account_id = connection.execute(text("""
            INSERT INTO cuentas (usuario_id,rol_id,username,password_hash,must_change_password,is_active)
            VALUES (:user,:role,:name,'NOT_A_REAL_LOGIN_HASH',true,true) RETURNING id
        """), {"user": user_id, "role": role_id, "name": "qa_" + token}).scalar_one()
    recipient = SimpleNamespace(user_id=user_id, account_id=account_id, role_id=role_id)
    try:
        yield recipient
    finally:
        with pg_cluster.engine.begin() as connection:
            assert_identity(connection, pg_cluster.manifest)
            connection.execute(text("UPDATE notificacion SET not_duplicada_de_id=NULL WHERE usu_id=:id"), {"id": user_id})
            connection.execute(text("DELETE FROM notificacion WHERE usu_id=:id"), {"id": user_id})
            connection.execute(text("DELETE FROM preferencia_notificacion WHERE usuario_id=:id"), {"id": user_id})
            connection.execute(text("DELETE FROM envio_notificacion_correo WHERE cuenta_id=:id"), {"id": account_id})
            connection.execute(text("DELETE FROM cuentas WHERE id=:id"), {"id": account_id})
            connection.execute(text("DELETE FROM usuarios WHERE id=:id"), {"id": user_id})
            connection.execute(text("DELETE FROM roles WHERE id=:id"), {"id": role_id})


@pytest.fixture(params=["boutique", "workshop"])
def synthetic_stock_source(pg_cluster, synthetic_recipient, request):
    """Real stock sources, categories and recipient role; no inventory service shortcuts."""
    kind = request.param
    token = uuid4().hex[:20]
    role = "INV_BOUTIQUE" if kind == "boutique" else "INV_TALLER"
    with pg_cluster.engine.begin() as connection:
        assert_identity(connection, pg_cluster.manifest)
        created_role_id = connection.execute(text("""
            INSERT INTO roles(codigo,nombre,activo) VALUES(:code,:name,true)
            ON CONFLICT(codigo) DO NOTHING RETURNING id
        """), {"code": role, "name": "QA STOCK " + token}).scalar_one_or_none()
        role_id = created_role_id or connection.execute(text("SELECT id FROM roles WHERE codigo=:code"), {"code": role}).scalar_one()
        connection.execute(text("UPDATE cuentas SET rol_id=:role WHERE id=:id"),
                           {"role": role_id, "id": synthetic_recipient.account_id})
        if kind == "boutique":
            type_id = connection.execute(text("INSERT INTO tipo_item_boutique(tib_nom,tib_hab) VALUES(:name,true) RETURNING tib_id"),
                                         {"name": "QA " + token}).scalar_one()
            source_id = connection.execute(text("""
                INSERT INTO item_boutique(tib_id,itb_cod,itb_nom,itb_color_prim,itb_material,itb_precio_compra,
                                         itb_precio_venta,itb_stock,itb_stock_min,itb_estado)
                VALUES(:type,:code,'QA SINTETICO','BLANCO','TEST',1,2,2,3,true) RETURNING itb_id
            """), {"type": type_id, "code": "QA_" + token}).scalar_one()
            table, key, type_table, type_key = "item_boutique", "itb_id", "tipo_item_boutique", "tib_id"
            notification_type = "STOCK_BAJO_BOUTIQUE"
        else:
            type_id = connection.execute(text("INSERT INTO tipo_inventario_taller(tit_nom,tit_hab) VALUES(:name,true) RETURNING tit_id"),
                                         {"name": "QA " + token}).scalar_one()
            source_id = connection.execute(text("""
                INSERT INTO inventario_taller(tit_id,int_cod,int_nom,int_color,int_costo_ref,int_stock,
                                             int_stock_min,int_uni_med,int_estado)
                VALUES(:type,:code,'QA SINTETICO','BLANCO',1,2,3,'metro',true) RETURNING int_id
            """), {"type": type_id, "code": "QA_" + token}).scalar_one()
            table, key, type_table, type_key = "inventario_taller", "int_id", "tipo_inventario_taller", "tit_id"
            notification_type = "STOCK_BAJO_TALLER"
    try:
        yield SimpleNamespace(kind=kind, id=source_id, type_id=type_id, table=table, key=key,
                              notification_type=notification_type, recipient=synthetic_recipient)
    finally:
        with pg_cluster.engine.begin() as connection:
            assert_identity(connection, pg_cluster.manifest)
            connection.execute(text("DELETE FROM notificacion WHERE not_tipo=:type AND not_tabla_ref=:table AND not_id_ref=:id"),
                               {"type": notification_type, "table": table.upper(), "id": source_id})
            # Identifiers below are selected exclusively by the fixture's fixed branches.
            connection.execute(text(f"DELETE FROM {table} WHERE {key}=:id"), {"id": source_id})
            connection.execute(text(f"DELETE FROM {type_table} WHERE {type_key}=:id"), {"id": type_id})
            connection.execute(text("UPDATE cuentas SET rol_id=:role WHERE id=:id"),
                               {"role": synthetic_recipient.role_id, "id": synthetic_recipient.account_id})
            if created_role_id is not None:
                connection.execute(text("DELETE FROM roles WHERE id=:id"), {"id": created_role_id})
