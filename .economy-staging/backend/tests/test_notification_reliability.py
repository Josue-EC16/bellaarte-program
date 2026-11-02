"""No-database regression checks; PostgreSQL execution lives in integration/."""

from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex

from app.core.notification_catalog import can_resolve_manually
from app.models.boutique_enums import PrioridadNotificacionEnum
from app.models.notification import Notificacion
from app.schemas.notification import NotificationQueryFilters, NotificationReadRequest
from app.services import notification_delivery_service as delivery
from app.services import notification_query_service as queries
from app.services import notification_sync_service as sync


NOW = datetime(2026, 10, 18, 12, tzinfo=timezone.utc)


class Result:
    def __init__(self, value=None, rowcount=0):
        self.value, self.rowcount = value, rowcount

    def scalar_one(self):
        return self.value

    scalar_one_or_none = scalar_one
    one = scalar_one

    def unique(self):
        return self

    scalars = unique

    def all(self):
        return self.value


class Database:
    def __init__(self, *results):
        self.results = list(results)
        self.statements = []
        self.info = {}
        self.commit = Mock()
        self.flush = Mock()

    def execute(self, statement, *args, **kwargs):
        self.statements.append(statement)
        return self.results.pop(0)


def sql(statement):
    return str(statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))


def account():
    return SimpleNamespace(usuario_id=71, rol=SimpleNamespace(codigo="ADMIN"))


def notification(**changes):
    recipient_account = SimpleNamespace(rol=SimpleNamespace(codigo="ADMIN", nombre="ADMIN"), username="qa")
    values = dict(id=8, tipo="STOCK_BAJO_BOUTIQUE", prioridad=PrioridadNotificacionEnum.ALTA,
                  titulo="STOCK BAJO", mensaje="CONDICION SINTETICA", modulo="BOUTIQUE", leida=False,
                  resuelta=False, fecha=NOW, fecha_leida=None, fecha_resuelta=None,
                  tabla_referencia="ITEM_BOUTIQUE", id_referencia=5, revision=1, revision_fecha=NOW,
                  motivo_cierre=None, duplicada_de_id=None, escritorio_revision_reclamada=0,
                  usuario=SimpleNamespace(id=71, nombre_completo="QA SINTETICO", cuenta=recipient_account))
    return SimpleNamespace(**{**values, **changes})


@pytest.mark.parametrize("kind", ["STOCK_BAJO_BOUTIQUE", "STOCK_BAJO_TALLER", "ENTREGA_PEDIDO_HOY",
                                  "PRUEBA_PEDIDO_HOY", "DEVOLUCION_FLETE_VENCIDA", "FLETE_MAX_SALIDAS",
                                  "ERROR_ENVIO_CORREO", "DESCONOCIDA"])
def test_condition_notifications_cannot_be_resolved_manually(kind):
    assert can_resolve_manually(kind) is False


@pytest.mark.parametrize("kind", ["SISTEMA", "PRUEBA_1_ALISTAR_MATERIAL", "PRUEBA_2_ALISTAR_MATERIAL"])
def test_manual_tasks_have_explicit_catalogue(kind):
    assert can_resolve_manually(kind.lower()) is True


@pytest.mark.parametrize('already_acknowledged', [False, True])
def test_material_reconciliation_does_not_reprogram_or_reopen_completed_task(monkeypatch, already_acknowledged):
    source = SimpleNamespace(numero=1, pedido=SimpleNamespace(habilitado=True,
                              estado_general=sync.EstadoPedidoGeneralEnum.ACTIVO))
    template = notification(tipo='PRUEBA_1_ALISTAR_MATERIAL', tabla_referencia='PRUEBA_PEDIDO')
    account_row = SimpleNamespace(usuario_id=71, usuario=SimpleNamespace(id=71))
    previous = notification(resuelta=True, motivo_cierre='MANUAL') if already_acknowledged else None
    db = Database(Result(None), Result(template), Result(rowcount=0), Result(previous))
    monkeypatch.setattr(sync, 'lock_test_source', lambda *_args: source)
    monkeypatch.setattr(sync, '_get_active_accounts_for_roles', lambda *_args: [account_row])
    create = Mock()
    monkeypatch.setattr(sync, 'create_notification_for_user', create)
    sync.reconcile_material_preparation_recipients(db, test_id=9)
    if already_acknowledged:
        create.assert_not_called()
    else:
        create.assert_called_once()
        assert create.call_args.kwargs['user'].id == 71
        assert not create.call_args.kwargs.get('force_recreate', False)
    db.commit.assert_not_called()


def test_updating_flete_limits_synchronizes_before_commit(monkeypatch):
    from app.services import flete_service as service
    from app.models.boutique_enums import EstadoFleteEnum

    entity = SimpleNamespace(id=12, habilitado=True, estado=EstadoFleteEnum.DISPONIBLE, salidas_actuales=2)
    actor = SimpleNamespace(usuario=SimpleNamespace())
    database = Mock()
    steps = []
    monkeypatch.setattr(service, 'lock_flete', lambda *_args: steps.append('lock'))
    monkeypatch.setattr(service, '_get_flete_entity', lambda *_args: entity)
    monkeypatch.setattr(service, '_recalculate_flete_state', lambda _entity: None)
    monkeypatch.setattr(service, 'register_audit_event', Mock())
    monkeypatch.setattr(service, 'sync_flete_max_outputs_notification', lambda *_args, **_kwargs: steps.append('sync'))
    monkeypatch.setattr(service, 'get_flete_detail', lambda *_args: entity)
    database.commit.side_effect = lambda: steps.append('commit')
    service.update_flete(database, flete_id=12,
        payload=SimpleNamespace(precio_flete_ref=25, max_salidas=4, observaciones=None),
        updated_by=actor, ip_address=None, user_agent=None)
    assert steps == ['lock', 'sync', 'commit']


@pytest.mark.parametrize("revision", [0, -1, None])
def test_read_requires_a_positive_revision(revision):
    with pytest.raises(ValidationError):
        NotificationReadRequest(revision=revision)


def test_admin_personal_list_ignores_requested_foreign_recipient():
    db = Database(Result(0), Result([]))
    result = queries.list_notifications(db, account=account(), filters=NotificationQueryFilters(user_id=999))
    assert result.items == []
    for statement in db.statements:
        assert "notificacion.usu_id = 71" in sql(statement)
        assert "notificacion.usu_id = 999" not in sql(statement)


def test_explicit_supervision_applies_recipient_and_bounded_pagination():
    db = Database(Result(201), Result([]))
    page = queries.list_notifications(db, account=account(), filters=NotificationQueryFilters(user_id=999),
                                      supervision=True, page=2, page_size=1000)
    assert (page.page, page.page_size, page.total) == (2, 100, 201)
    statement = sql(db.statements[-1])
    assert "notificacion.usu_id = 999" in statement
    assert "LIMIT 100 OFFSET 100" in statement


def test_summary_admin_is_personal_and_resolved_rows_do_not_count():
    db = Database(Result((1, 2, 0)), Result([]), Result([]))
    result = queries.get_notification_summary(db, account=account())
    assert (result.unread_count, result.unresolved_count) == (1, 2)
    for statement in db.statements:
        query = sql(statement)
        assert "notificacion.usu_id = 71" in query
        assert "notificacion.not_resuelta IS false" in query


def test_stale_read_does_not_acknowledge_new_revision():
    entity = notification(revision=2)
    db = Database(Result(entity))
    with pytest.raises(HTTPException) as error:
        queries.mark_notification_read(db, notification_id=8, account=account(), revision=1)
    assert error.value.status_code == 409
    assert entity.leida is False
    db.commit.assert_not_called()
    assert "FOR UPDATE" in sql(db.statements[0])


def test_read_all_uses_personal_revision_snapshot():
    db = Database(Result(rowcount=0))
    assert queries.mark_all_notifications_read(db, account=account()) == {"updated": 0}
    query = sql(db.statements[0])
    assert "notificacion.usu_id = 71" in query
    assert "notificacion.not_revision = pending_snapshot.observed_revision" in query
    assert "MATERIALIZED" in query
    db.commit.assert_called_once()


@pytest.mark.parametrize("kind", ["STOCK_BAJO_BOUTIQUE", "STOCK_BAJO_TALLER"])
def test_resolve_rejects_stock_before_mutation_or_commit(kind):
    entity = notification(tipo=kind)
    db = Database(Result(entity))
    with pytest.raises(HTTPException) as error:
        queries.resolve_notification(db, notification_id=8, reason="QA", resolved_by=account(),
                                     ip_address=None, user_agent=None)
    assert error.value.status_code == 409
    assert entity.resuelta is False
    db.commit.assert_not_called()


def test_open_unique_index_treats_nulls_as_equal():
    index = next(index for index in Notificacion.__table__.indexes if index.name == "ux_notificacion_abierta")
    query = str(CreateIndex(index).compile(dialect=postgresql.dialect()))
    assert "UNIQUE INDEX" in query
    assert "NULLS NOT DISTINCT" in query
    assert "WHERE not_resuelta = false" in query


def test_upsert_uses_open_key_and_null_safe_fallback():
    user = SimpleNamespace(id=71, activo=True,
                           cuenta=SimpleNamespace(is_active=True, rol=SimpleNamespace(activo=True)))
    existing = notification(leida=True)
    db = Database(Result(None), Result(None), Result(existing))
    db.info["notification_counters"] = {}
    returned = sync.create_notification_for_user(db, user=user, tipo=" sistema ",
        prioridad=PrioridadNotificacionEnum.MEDIA, titulo="QA", mensaje="SIN CAMBIO", modulo=None,
        tabla_referencia=None, id_referencia=None)
    assert returned is existing
    compiled = sql(db.statements[0])
    assert "ON CONFLICT" in compiled
    assert "not_resuelta IS false" in compiled or "not_resuelta = false" in compiled
    assert sql(db.statements[-1]).count("IS NOT DISTINCT FROM NULL") == 2
    assert existing.leida is True
    assert db.info["notification_counters"] == {"unchanged": 1}
    db.commit.assert_not_called()


def test_disabled_desktop_does_not_scan_or_claim_notifications():
    db = Database(Result(None))
    assert delivery.claim_desktop_notifications(db, account=account()).items == []
    assert len(db.statements) == 1


def test_desktop_claim_is_personal_recent_unread_open_and_bounded(monkeypatch):
    monkeypatch.setattr(delivery, "utc_now", lambda: NOW)
    row = notification()
    preference = SimpleNamespace(escritorio_habilitado_desde=NOW - timedelta(days=1))
    db = Database(Result(preference), Result([row]))
    response = delivery.claim_desktop_notifications(db, account=account())
    assert [item.id for item in response.items] == [8]
    assert row.escritorio_revision_reclamada == row.revision
    query = sql(db.statements[1])
    for required in ["notificacion.usu_id = 71", "notificacion.not_resuelta IS false",
                     "notificacion.not_leida IS false", "LIMIT 3", "FOR UPDATE SKIP LOCKED",
                     (NOW - timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")]:
        assert required in query
    db.commit.assert_called_once()


def test_desktop_enable_is_idempotent_and_optout_clears_cutoff(monkeypatch):
    started = NOW - timedelta(minutes=2)
    preference = SimpleNamespace(escritorio_habilitado_desde=started)
    db = Database(Result(), Result(preference))
    monkeypatch.setattr(delivery, "utc_now", lambda: NOW)
    enabled = delivery.set_notification_preferences(db, account=account(), desktop_enabled=True)
    assert enabled.desktop_enabled_since == started
    db = Database(Result(), Result(preference))
    disabled = delivery.set_notification_preferences(db, account=account(), desktop_enabled=False)
    assert disabled.desktop_enabled is False
    assert preference.escritorio_habilitado_desde is None


@pytest.mark.parametrize("kind", ["boutique", "workshop"])
@pytest.mark.parametrize("active,enabled,stock,expected_open", [
    (True, True, 2, True), (True, True, 0, True), (True, True, 3, False),
    (False, True, 1, False), (True, False, 1, False),
])
def test_stock_incident_only_remains_open_while_source_condition_is_valid(monkeypatch, kind, active, enabled, stock, expected_open):
    item = SimpleNamespace(id=5, estado=active, stock=stock, stock_minimo=2, nombre="QA",
        tipo_item=SimpleNamespace(habilitado=enabled), tipo=SimpleNamespace(habilitado=enabled),
        unidad_medida=SimpleNamespace(value="metro"))
    monkeypatch.setattr(sync, "lock_source", lambda *_args: item)
    create = Mock()
    resolve = Mock()
    monkeypatch.setattr(sync, "_sync_role_notifications_for_reference", create)
    monkeypatch.setattr(sync, "resolve_notifications_by_reference", resolve)
    synchronize = sync.sync_boutique_stock_notification if kind == "boutique" else sync.sync_workshop_stock_notification
    synchronize(Database(), item_id=5)
    if expected_open:
        create.assert_called_once()
        resolve.assert_not_called()
        assert create.call_args.kwargs["stock_zero"] is (stock == 0)
        expected = PrioridadNotificacionEnum.URGENTE if stock == 0 else PrioridadNotificacionEnum.ALTA
        assert create.call_args.kwargs["prioridad"] == expected
    else:
        resolve.assert_called_once()
        create.assert_not_called()


def test_base_runner_rejects_integration_before_spawning_a_child():
    path = Path(__file__).resolve().parents[1] / "scripts" / "run_base_tests.py"
    spec = importlib.util.spec_from_file_location("base_test_selection_guard", path)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    with pytest.raises(ValueError, match="isolated integration runner"):
        runner._test_targets(["tests/integration/test_notification_postgresql.py"])
