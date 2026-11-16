"""Pure TC-01 contracts; PostgreSQL behavior is covered by integration tests."""
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from fastapi import HTTPException
import pytest
from sqlalchemy.schema import CreateIndex
from sqlalchemy.dialects import postgresql

from app.models.exchange_rate import TipoCambioMoneda
from app.models.exchange_rate_record import TipoCambioRegistro
from app.services.exchange_rate_history_service import aware_datetime, finish_failure, validate_history_rows, validate_rate


@pytest.mark.parametrize("value", ["6.9600", Decimal("6.9600"), "0.0001", "99999999.9999", "6.96000", 1])
def test_decimal_rate_preserves_exact_numeric_precision(value):
    assert isinstance(validate_rate(value), Decimal)


@pytest.mark.parametrize("value", ["0", "-1", "NaN", "Infinity", "100000000", "6.12345", 6.96, True, None])
def test_rate_rejects_float_nonfinite_out_of_range_and_implicit_rounding(value):
    with pytest.raises(HTTPException) as error:
        validate_rate(value)
    assert error.value.status_code == 422


def provenance(**changes):
    result = dict(verified=True, official_source="BCB verified local archive", verified_by="Human reviewer",
        verified_at="2026-11-01T10:00:00-04:00", dataset_sha256="a" * 64,
        period_start="2026-10-01", period_end="2026-10-31")
    result.update(changes)
    return result


def test_history_allows_repeated_values_on_different_verified_days():
    rows = validate_history_rows([
        {"fecha_objetivo": f"2026-10-{day:02}", "valor_bob": "6.9600"}
        for day in range(31, 0, -1)
    ], provenance())
    assert len(rows) == 31
    assert [row["fecha_objetivo"] for row in rows[:2]] == [date(2026, 10, 1), date(2026, 10, 2)]
    assert rows[0]["valor_bob"] == rows[1]["valor_bob"] == Decimal("6.9600")


def test_initial_history_rejects_gaps_without_fabricating_daily_values():
    with pytest.raises(HTTPException) as error:
        validate_history_rows([{"fecha_objetivo": "2026-10-01", "valor_bob": "6.9600"}], provenance())
    assert error.value.status_code == 422


@pytest.mark.parametrize("changes", [{"verified": False}, {"dataset_sha256": "bad"},
    {"official_source": " "}, {"verified_by": ""}, {"verified_at": "2026-10-01"},
    {"period_start": "2026-10-02"}, {"period_end": "2026-11-01"}])
def test_history_requires_explicit_verified_one_month_provenance(changes):
    with pytest.raises(HTTPException):
        validate_history_rows([{"fecha_objetivo": "2026-10-01", "valor_bob": "6.96"}], provenance(**changes))


@pytest.mark.parametrize("rows", [[], [{"fecha_objetivo": "2026-09-30", "valor_bob": "6.96"}],
    [{"fecha_objetivo": "2026-10-01", "valor_bob": "6.96"}] * 2])
def test_history_rejects_empty_out_of_period_and_duplicate_dates(rows):
    with pytest.raises(HTTPException):
        validate_history_rows(rows, provenance())


def test_timezone_is_mandatory_and_preserved_as_a_real_instant():
    with pytest.raises(HTTPException):
        aware_datetime(datetime(2026, 10, 1))
    assert aware_datetime(datetime(2026, 10, 1, tzinfo=timezone.utc)).tzinfo == timezone.utc


def test_disabled_currency_does_not_prevent_reconciling_an_interrupted_attempt():
    started = datetime(2026, 10, 1, tzinfo=timezone.utc)
    item = SimpleNamespace(id=4, moneda_id=2, proveedor="FACTURA_BO_BCB", estado="INICIADO",
        fecha_intento=started, codigo_http=None, proximo_intento=None)
    db = Mock()
    db.scalar.return_value = 2
    currency_result = Mock()
    currency_result.scalar_one_or_none.return_value = SimpleNamespace(id=2, codigo="USD", habilitado=False)
    attempt_result = Mock()
    attempt_result.scalar_one.return_value = item
    db.execute.side_effect = [currency_result, attempt_result]
    result = finish_failure(db, attempt_id=4, estado="ERROR_EJECUCION")
    assert result.estado == "ERROR_EJECUCION"
    db.commit.assert_called_once()


def test_approved_physical_columns_and_decimal_storage():
    assert set(TipoCambioRegistro.__table__.columns.keys()) == {"tcs_id", "mon_id", "tcm_id", "tcs_fecha_objetivo",
        "tcs_num_intento", "tcs_fec_intento", "tcs_estado", "tcs_codigo_http", "tcs_proximo_intento", "tcs_proveedor"}
    assert set(TipoCambioMoneda.__table__.columns.keys()) == {"tcm_id", "mon_id", "usu_id", "tcm_valor_bob",
        "tcm_fec_reg", "tcm_obs", "tcm_activo", "tcm_origen", "tcm_fuente", "tcm_fec_consulta"}
    assert TipoCambioMoneda.__table__.c.tcm_valor_bob.type.precision == 12
    assert TipoCambioMoneda.__table__.c.tcm_valor_bob.type.scale == 4
    assert TipoCambioMoneda.__table__.c.usu_id.nullable is True


def test_execution_day_index_has_explicit_bolivian_timezone_and_automatic_predicate():
    index = next(index for index in TipoCambioRegistro.__table__.indexes if index.name == "uq_tcs_ordinal_dia")
    sql = str(CreateIndex(index).compile(dialect=postgresql.dialect()))
    assert "America/La_Paz" in sql and "tcs_num_intento>0" in sql and "UNIQUE" in sql


def test_offline_import_checks_dataset_hash_before_any_database_operation(tmp_path):
    script = Path(__file__).resolve().parents[1] / "scripts/import_exchange_rate_history.py"
    spec = importlib.util.spec_from_file_location("tc_history_import_test", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    csv_file, manifest_file = tmp_path / "dataset.csv", tmp_path / "provenance.json"
    csv_file.write_text("fecha_objetivo,valor_bob\n" + "".join(
        f"2026-10-{day:02},6.9600\n" for day in range(1, 32)), encoding="utf-8")
    manifest_file.write_text(json.dumps(provenance(dataset_sha256=hashlib.sha256(csv_file.read_bytes()).hexdigest())), encoding="utf-8")
    rows, proof = module.read_verified_dataset(csv_file, manifest_file)
    assert len(rows) == 31 and proof["verified"]
    csv_file.write_text("fecha_objetivo,valor_bob\n2026-10-01,9.9600\n", encoding="utf-8")
    with pytest.raises(HTTPException):
        module.read_verified_dataset(csv_file, manifest_file)
