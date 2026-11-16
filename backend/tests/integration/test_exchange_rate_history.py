"""SPEC-TC-01 only on manifest-validated PostgreSQL, with synthetic data."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import importlib.util
from pathlib import Path
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4
from zoneinfo import ZoneInfo

import casbin
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


def _setup(db):
    from test_economy_transactions import _setup as economy_setup
    from app.models.currency import Moneda
    state = economy_setup(db)
    usd = db.scalar(select(Moneda).where(Moneda.codigo == "USD"))
    if usd is None:
        usd = Moneda(codigo="USD", nombre="DOLAR QA", simbolo="$", es_base=False, habilitado=True)
        db.add(usd)
        db.flush()
    state.usd = usd
    db.commit()
    return state


@pytest.fixture
def tc(pg_cluster):
    with pg_cluster.engine.connect() as connection:
        pg_cluster.assert_identity(connection, pg_cluster.manifest)
        connection.rollback()
        transaction = connection.begin()
        db = Session(connection, autoflush=False, join_transaction_mode="create_savepoint", expire_on_commit=False)
        try:
            yield _setup(db)
        finally:
            db.close()
            transaction.rollback()


def _manual(tc, value="6.9600"):
    from app.services.currency_service import create_exchange_rate
    from app.schemas.currency import TipoCambioCreateRequest
    return create_exchange_rate(tc.db, payload=TipoCambioCreateRequest(moneda_id=tc.usd.id, valor_bob=value),
        created_by=tc.admin, ip_address=None, user_agent="QA_TC01")


def _today():
    return datetime.now(ZoneInfo("America/La_Paz")).date()


def test_exact_new_columns_types_indexes_and_existing_invariants(tc):
    db = tc.db
    names = list(db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='tipo_cambio_registros' ORDER BY ordinal_position")).scalars())
    assert names == ["tcs_id", "mon_id", "tcm_id", "tcs_fecha_objetivo", "tcs_num_intento", "tcs_fec_intento", "tcs_estado", "tcs_codigo_http", "tcs_proximo_intento", "tcs_proveedor"]
    rate_names = set(db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='tipo_cambio_moneda'")).scalars())
    assert rate_names == {"tcm_id", "mon_id", "usu_id", "tcm_valor_bob", "tcm_fec_reg", "tcm_obs", "tcm_activo", "tcm_origen", "tcm_fuente", "tcm_fec_consulta"}
    assert db.scalar(text("SELECT numeric_scale FROM information_schema.columns WHERE table_schema='public' AND table_name='tipo_cambio_moneda' AND column_name='tcm_valor_bob'")) == 4
    assert db.scalar(text("SELECT count(*) FROM pg_trigger WHERE tgrelid='tipo_cambio_moneda'::regclass AND tgname='trg_auditoria_tipo_cambio_moneda'")) == 0
    assert db.scalar(text("SELECT count(*) FROM pg_trigger WHERE tgrelid='moneda'::regclass AND tgname='trg_auditoria_moneda'")) == 1


def test_new_manual_rate_replaces_only_its_currency_and_patch_preserves_old_value(tc):
    from app.models.exchange_rate import TipoCambioMoneda
    from app.schemas.currency import TipoCambioUpdateRequest
    from app.services.currency_service import update_exchange_rate, set_exchange_rate_status
    first = _manual(tc)
    second = update_exchange_rate(tc.db, rate_id=first.id, payload=TipoCambioUpdateRequest(valor_bob="7.0100"),
        updated_by=tc.admin, ip_address=None, user_agent="QA_TC01")
    assert second.id != first.id and second.activo
    tc.db.expire_all()
    old = tc.db.get(TipoCambioMoneda, first.id)
    assert old.valor_bob == Decimal("6.9600") and not old.activo
    assert tc.db.scalar(select(func.count()).select_from(TipoCambioMoneda).where(TipoCambioMoneda.moneda_id == tc.usd.id, TipoCambioMoneda.activo)) == 1
    observed = update_exchange_rate(tc.db, rate_id=old.id, payload=TipoCambioUpdateRequest(observaciones="HISTORICO"),
        updated_by=tc.admin, ip_address=None, user_agent="QA_TC01")
    assert observed.id == old.id and not observed.activo and observed.valor_bob == Decimal("6.9600")
    with pytest.raises(HTTPException) as error:
        set_exchange_rate_status(tc.db, rate_id=old.id, active=True, changed_by=tc.admin, ip_address=None, user_agent="QA_TC01")
    assert error.value.status_code == 409


def test_rates_do_not_add_general_audit_rows_and_previous_audit_is_preserved(tc):
    from app.services.currency_service import set_exchange_rate_status
    before = tc.db.scalar(text("SELECT count(*) FROM auditoria_sistema WHERE aud_tabla='tipo_cambio_moneda'"))
    created = _manual(tc)
    set_exchange_rate_status(tc.db, rate_id=created.id, active=False, changed_by=tc.admin, ip_address=None, user_agent="QA_TC01")
    assert tc.db.scalar(text("SELECT count(*) FROM auditoria_sistema WHERE aud_tabla='tipo_cambio_moneda'")) == before


@pytest.fixture
def tc_api(tc):
    from app.api.routers.currencies import router
    from app.core.database import get_db
    from app.deps.auth import get_enforcer
    from app.services.auth_session_service import create_session
    directory = Path(__file__).resolve().parents[2] / "app/security"
    enforcer = casbin.Enforcer(str(directory / "model.conf"), str(directory / "policy.csv"))
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/monedas")
    def database():
        yield tc.db
    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_enforcer] = lambda: enforcer
    def headers(actor):
        token = create_session(tc.db, actor)["access_token"]
        tc.db.commit()
        return {"Authorization": "Bearer " + token}
    with TestClient(app) as client:
        yield client, headers


def test_api_decimal_permissions_and_automatic_immutable_even_for_admin(tc, tc_api):
    from app.services.exchange_rate_history_service import insert_rate
    client, headers = tc_api
    auth = headers(tc.admin)
    created = client.post("/api/v1/monedas/tipos-cambio", headers=auth, json={"moneda_id": tc.usd.id, "valor_bob": "6.9600"})
    assert created.status_code == 201, created.text
    assert created.json()["valor_bob"] == "6.9600"
    assert created.json()["origen"] == "MANUAL"
    assert client.post("/api/v1/monedas/tipos-cambio", headers=headers(tc.cashier), json={"moneda_id": tc.usd.id, "valor_bob": "7"}).status_code == 403
    auto = insert_rate(tc.db, moneda_id=tc.usd.id, valor_bob="6.9700", usuario_id=None, origen="AUTOMATICO",
        fuente="BCB_VIA_FACTURA_BO", fec_consulta=datetime.now(timezone.utc), operativo=True)
    auto_id = auto.id
    tc.db.commit()
    for endpoint, payload in [(f"/{auto_id}", {"valor_bob": "8"}), (f"/{auto_id}", {"observaciones": "ALTERADO"}), (f"/{auto_id}/status", {"activo": False})]:
        result = client.patch("/api/v1/monedas/tipos-cambio" + endpoint, headers=auth, json=payload)
        assert result.status_code == 409, result.text
    detail = client.get(f"/api/v1/monedas/tipos-cambio/{auto_id}", headers=auth)
    assert detail.status_code == 200 and detail.json()["registrado_por"] == "SISTEMA"


def test_automatic_attempt_repeated_rate_daily_and_recovery_stays_inactive(tc):
    from app.services.exchange_rate_history_service import begin_attempt, finish_success
    from app.models.exchange_rate import TipoCambioMoneda
    current = _manual(tc, "7.0000")
    for days_ago in (2, 1):
        attempt = begin_attempt(tc.db, moneda_id=tc.usd.id, fecha_objetivo=_today() - timedelta(days=days_ago))
        completed = finish_success(tc.db, attempt_id=attempt.id, valor_bob="6.9600", fec_consulta=datetime.now(timezone.utc), operativo=False)
        assert completed.estado == "EXITOSO"
        rate = tc.db.get(TipoCambioMoneda, completed.tipo_cambio_id)
        assert not rate.activo and rate.usuario_id is None and rate.valor_bob == Decimal("6.9600")
        assert rate.fecha_registro.date() >= date.today() - timedelta(days=1)
    tc.db.expire_all()
    assert tc.db.get(TipoCambioMoneda, current.id).activo
    attempt = begin_attempt(tc.db, moneda_id=tc.usd.id, fecha_objetivo=_today())
    completed = finish_success(tc.db, attempt_id=attempt.id, valor_bob="6.9600", fec_consulta=datetime.now(timezone.utc))
    assert tc.db.get(TipoCambioMoneda, completed.tipo_cambio_id).activo
    tc.db.expire_all()
    assert not tc.db.get(TipoCambioMoneda, current.id).activo


def test_failure_and_budget_do_not_create_rates(tc):
    from app.models.exchange_rate import TipoCambioMoneda
    from app.services.exchange_rate_history_service import begin_attempt, finish_failure
    before = tc.db.scalar(select(func.count()).select_from(TipoCambioMoneda))
    for number in range(1, 11):
        attempt = begin_attempt(tc.db, moneda_id=tc.usd.id, fecha_objetivo=_today())
        assert attempt.numero_intento == number
        failed = finish_failure(tc.db, attempt_id=attempt.id, estado="ERROR_CONEXION")
        assert failed.tipo_cambio_id is None
    with pytest.raises(HTTPException):
        begin_attempt(tc.db, moneda_id=tc.usd.id, fecha_objetivo=_today())
    tc.db.rollback()
    assert tc.db.scalar(select(func.count()).select_from(TipoCambioMoneda)) == before


def test_manual_creation_failure_rolls_back_deactivation(tc, monkeypatch):
    from app.models.exchange_rate import TipoCambioMoneda
    from app.services import currency_service
    first = _manual(tc)
    original = currency_service.insert_rate
    def failing(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("Injected before commit")
    monkeypatch.setattr(currency_service, "insert_rate", failing)
    with pytest.raises(RuntimeError):
        _manual(tc, "7.0000")
    assert tc.db.get(TipoCambioMoneda, first.id).activo


def test_currency_report_accepts_multiple_rates_and_keeps_latest_distinct_from_active(tc):
    from app.services.module_report_service import get_currencies_report
    from app.services.exchange_rate_history_service import insert_rate
    _manual(tc)
    inserted = insert_rate(tc.db, moneda_id=tc.usd.id, valor_bob="6.8000", usuario_id=None, origen="AUTOMATICO",
        fuente="BCB_CARGA_INICIAL", operativo=False)
    tc.db.commit()
    report = get_currencies_report(tc.db, currency_id=tc.usd.id)
    latest = next(item for item in report.table_rows["latest_rates"] if item["currency"] == "USD")
    assert latest["value_bob"] == "6.8000" and not latest["active"]


def test_commercial_snapshots_before_and_after_new_rate_are_frozen(tc):
    from app.schemas.boutique import BoutiqueSaleCreateRequest
    from app.schemas.order import OrderPaymentCreateRequest
    from app.schemas.flete import SalidaFleteCreateRequest
    from app.services.boutique_sale_service import create_boutique_sale
    from app.services.order_payment_service import create_order_payment
    from app.services.flete_service import create_flete_output
    def operations(state):
        sale = create_boutique_sale(state.db, payload=BoutiqueSaleCreateRequest(item_id=state.item.id, client_id=state.client.id,
            currency_id=state.usd.id, quantity=1, payment_method="qr"), created_by=state.cashier, ip_address=None, user_agent="QA_TC01")
        payment = create_order_payment(state.db, order_id=state.order.id,
            payload=OrderPaymentCreateRequest(currency_id=state.usd.id, monto=10, metodo_pago="qr"),
            created_by=state.cashier, ip_address=None, user_agent="QA_TC01")
        output = create_flete_output(state.db, payload=SalidaFleteCreateRequest(flete_id=state.flete.id,
            client_id=state.client.id, currency_id=state.usd.id, fecha_salida=date.today(),
            fecha_devolucion_prevista=date.today() + timedelta(days=2), precio=100, garantia=200,
            metodo_pago="qr", estado_entrega="bueno"),
            created_by=state.cashier, ip_address=None, user_agent="QA_TC01")
        return sale, payment, output
    _manual(tc, "6.9600")
    before = operations(tc)
    second = _setup(tc.db)
    _manual(tc, "7.0100")
    after = operations(second)
    from app.models.boutique_sale import VentaBoutique
    from app.models.order import PagoPedido
    from app.models.flete import SalidaFlete
    tc.db.expire_all()
    for responses, expected in ((before, Decimal("6.9600")), (after, Decimal("7.0100"))):
        for model, response in zip((VentaBoutique, PagoPedido, SalidaFlete), responses):
            origin = tc.db.get(model, response.id)
            assert origin.tipo_cambio_usado == expected
            assert origin.comprobante.tipo_cambio_usado == expected


@pytest.mark.parametrize("second_origin", ["MANUAL", "AUTOMATICO"])
def test_concurrent_insertions_commit_one_active_per_currency(pg_cluster, second_origin):
    from app.models.account import Cuenta
    from app.models.exchange_rate import TipoCambioMoneda
    from app.services.currency_service import create_exchange_rate
    from app.schemas.currency import TipoCambioCreateRequest
    from app.services.exchange_rate_history_service import begin_attempt, finish_success
    with Session(pg_cluster.engine, expire_on_commit=False) as db:
        state = _setup(db)
        actor_id, moneda_id = state.admin.id, state.usd.id
        attempt_id = begin_attempt(db, moneda_id=moneda_id, fecha_objetivo=_today()).id if second_origin == "AUTOMATICO" else None
    barrier = Barrier(2)
    def insert(value):
        with Session(pg_cluster.engine, autoflush=False) as db:
            actor = db.get(Cuenta, actor_id)
            barrier.wait(timeout=10)
            if value == "7.0100" and attempt_id is not None:
                return finish_success(db, attempt_id=attempt_id, valor_bob=value,
                    fec_consulta=datetime.now(timezone.utc)).tipo_cambio_id
            return create_exchange_rate(db, payload=TipoCambioCreateRequest(moneda_id=moneda_id, valor_bob=value),
                created_by=actor, ip_address=None, user_agent="QA_TC_CONCURRENT").id
    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = pool.submit(insert, "6.9600"), pool.submit(insert, "7.0100")
        assert first.result(timeout=20) != second.result(timeout=20)
    with Session(pg_cluster.engine) as db:
        assert db.scalar(select(func.count()).select_from(TipoCambioMoneda).where(TipoCambioMoneda.moneda_id == moneda_id, TipoCambioMoneda.activo)) == 1
        if attempt_id is not None:
            # Remove only this test's technical success so future test runs can
            # exercise the same execution date without inheriting an outcome.
            db.execute(text("DELETE FROM tipo_cambio_registros WHERE tcs_id=:id"), {"id": attempt_id})
            db.commit()


def test_database_rejects_nan_even_though_postgresql_nan_compares_greater_than_zero(tc):
    with pytest.raises(IntegrityError):
        with tc.db.begin_nested():
            tc.db.execute(text("""INSERT INTO tipo_cambio_moneda(mon_id,usu_id,tcm_valor_bob,tcm_activo)
                VALUES(:mon,:user,'NaN'::numeric,false)"""), {"mon": tc.usd.id, "user": tc.admin.usuario_id})


def test_attempt_ordinal_is_unique_by_execution_day_not_target_date(tc):
    from app.models.exchange_rate_record import TipoCambioRegistro
    from app.services.exchange_rate_history_service import begin_attempt
    attempt = begin_attempt(tc.db, moneda_id=tc.usd.id, fecha_objetivo=_today())
    with pytest.raises(IntegrityError):
        with tc.db.begin_nested():
            tc.db.add(TipoCambioRegistro(moneda_id=tc.usd.id, fecha_objetivo=_today() - timedelta(days=1),
                numero_intento=attempt.numero_intento, fecha_intento=attempt.fecha_intento + timedelta(seconds=1),
                estado="INICIADO", proveedor=attempt.proveedor))
            tc.db.flush()


def test_attempt_ordinal_resets_at_bolivian_midnight(tc):
    from app.services.exchange_rate_history_service import begin_attempt, finish_failure
    local_today = _today()
    before_midnight = datetime.combine(local_today - timedelta(days=1), datetime.min.time(), tzinfo=ZoneInfo("America/La_Paz")) + timedelta(hours=23, minutes=59)
    after_midnight = before_midnight + timedelta(minutes=2)
    previous = begin_attempt(tc.db, moneda_id=tc.usd.id, fecha_objetivo=local_today - timedelta(days=2), now=before_midnight)
    finish_failure(tc.db, attempt_id=previous.id, estado="ERROR_EJECUCION")
    following = begin_attempt(tc.db, moneda_id=tc.usd.id, fecha_objetivo=local_today - timedelta(days=2), now=after_midnight)
    assert previous.numero_intento == following.numero_intento == 1


def test_record_cannot_link_a_rate_from_another_currency(tc):
    from app.models.exchange_rate_record import TipoCambioRegistro
    from app.services.exchange_rate_history_service import insert_rate
    bob = insert_rate(tc.db, moneda_id=tc.currency.id, valor_bob=Decimal("1"), usuario_id=tc.admin.usuario_id)
    tc.db.commit()
    with pytest.raises(IntegrityError):
        with tc.db.begin_nested():
            tc.db.add(TipoCambioRegistro(moneda_id=tc.usd.id, tipo_cambio_id=bob.id, fecha_objetivo=_today(),
                numero_intento=0, fecha_intento=datetime.now(timezone.utc), estado="CARGA_HISTORICA", proveedor="BCB_CARGA_INICIAL"))
            tc.db.flush()


def _synthetic_month_history():
    first = _today().replace(day=1) - timedelta(days=1)
    last = first
    first = first.replace(day=1)
    rows = [{"fecha_objetivo": (first + timedelta(days=offset)).isoformat(), "valor_bob": "6.9600"}
        for offset in range((last - first).days + 1)]
    proof = {"verified": True, "official_source": "SYNTHETIC_QA_NOT_A_REAL_BCB_DATASET", "verified_by": "QA",
        "dataset_sha256": "a" * 64, "period_start": first.isoformat(), "period_end": last.isoformat(),
        "verified_at": datetime.now(timezone.utc).isoformat()}
    return rows, proof


def test_initial_history_is_idempotent_inactive_and_does_not_consume_attempt_budget(tc):
    from app.models.exchange_rate import TipoCambioMoneda
    from app.services.exchange_rate_history_service import import_history, begin_attempt
    current = _manual(tc, "7.0100")
    rows, proof = _synthetic_month_history()
    assert import_history(tc.db, rows=rows, provenance=proof)["inserted"] == len(rows)
    assert import_history(tc.db, rows=rows, provenance=proof)["skipped"] == len(rows)
    tc.db.expire_all()
    assert tc.db.get(TipoCambioMoneda, current.id).activo
    assert begin_attempt(tc.db, moneda_id=tc.usd.id, fecha_objetivo=_today()).numero_intento == 1


def test_initial_history_conflict_rolls_back_whole_batch(tc):
    from app.models.exchange_rate_record import TipoCambioRegistro
    from app.services.exchange_rate_history_service import import_history
    rows, proof = _synthetic_month_history()
    import_history(tc.db, rows=rows, provenance=proof)
    total = tc.db.scalar(select(func.count()).select_from(TipoCambioRegistro))
    rows[1]["valor_bob"] = "7.0100"
    with pytest.raises(HTTPException) as error:
        import_history(tc.db, rows=rows, provenance=proof)
    assert error.value.status_code == 409
    assert tc.db.scalar(select(func.count()).select_from(TipoCambioRegistro)) == total


def test_0023_migration_roundtrip_without_losing_business_rows(pg_cluster):
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import create_engine
    from sqlalchemy.engine import make_url
    migration_file = Path(__file__).resolve().parents[2] / "alembic/versions/20261104_0023_exchange_rate_history.py"
    spec = importlib.util.spec_from_file_location("reviewed_exchange_rate_history", migration_file)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with pg_cluster.migration_engine.connect() as connection:
        pg_cluster.assert_identity(connection, pg_cluster.manifest, migrator=True)
        connection.rollback()
        transaction = connection.begin()
        try:
            # Discard only this transaction's new test history, then roll back
            # every DDL/DML step at the end; the cluster keeps its exact data.
            connection.execute(text("DELETE FROM tipo_cambio_registros"))
            connection.execute(text("DELETE FROM tipo_cambio_moneda WHERE tcm_origen='AUTOMATICO'"))
            connection.execute(text("UPDATE tipo_cambio_moneda SET tcm_fuente=NULL,tcm_fec_consulta=NULL"))
            before = connection.execute(text("SELECT count(*),sum(tcm_valor_bob) FROM tipo_cambio_moneda")).one()
            with Operations.context(MigrationContext.configure(connection)):
                migration.downgrade()
                assert connection.scalar(text("SELECT to_regclass('tipo_cambio_registros')")) is None
                migration.upgrade()
                assert tuple(connection.execute(text("SELECT count(*),sum(tcm_valor_bob) FROM tipo_cambio_moneda")).one()) == tuple(before)
                assert connection.scalar(text("SELECT count(*) FROM tipo_cambio_moneda WHERE tcm_origen<>'MANUAL'")) == 0
        finally:
            transaction.rollback()


def test_0023_downgrade_refuses_new_history_instead_of_discarding_it(tc):
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from app.services.exchange_rate_history_service import begin_attempt
    begin_attempt(tc.db, moneda_id=tc.usd.id, fecha_objetivo=_today())
    migration_file = Path(__file__).resolve().parents[2] / "alembic/versions/20261104_0023_exchange_rate_history.py"
    spec = importlib.util.spec_from_file_location("guarded_exchange_rate_history", migration_file)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with Operations.context(MigrationContext.configure(tc.db.connection())):
        with pytest.raises(RuntimeError):
            migration.downgrade()
