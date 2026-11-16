from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.schemas.currency import TipoCambioCreateRequest, TipoCambioUpdateRequest
from app.services.currency_service import _ensure_exchange_admin, _ensure_manual


@pytest.mark.parametrize("value", ["0", "-1", "NaN", "Infinity", "100000000", "6.12345"])
def test_rate_contract_rejects_nonpositive_nonfinite_overflow_and_excess_scale(value):
    for contract, extra in ((TipoCambioCreateRequest, {"moneda_id": 1}), (TipoCambioUpdateRequest, {})):
        with pytest.raises(ValidationError):
            contract(valor_bob=value, **extra)


def test_rate_contract_preserves_decimal_and_cannot_choose_automatic_provenance():
    payload = TipoCambioCreateRequest(moneda_id=1, valor_bob="6.9600")
    assert payload.valor_bob == Decimal("6.9600")
    assert isinstance(payload.valor_bob, Decimal)
    assert payload.model_dump(mode="json")["valor_bob"] == "6.9600"
    with pytest.raises(ValidationError):
        TipoCambioCreateRequest(moneda_id=1, valor_bob="6.96", origen="AUTOMATICO")
    with pytest.raises(ValidationError):
        TipoCambioCreateRequest(moneda_id=1, valor_bob="6.96", activo=False)


def test_observation_only_patch_does_not_invent_value_or_status():
    payload = TipoCambioUpdateRequest(observaciones="REFERENCIA")
    assert payload.valor_bob is None and payload.activo is None
    assert payload.model_fields_set == {"observaciones"}


def test_automatic_rate_rejects_human_mutation_and_non_admin_cannot_manage_rates():
    with pytest.raises(HTTPException) as error:
        _ensure_manual(SimpleNamespace(origen="AUTOMATICO"))
    assert error.value.status_code == 409
    actor = SimpleNamespace(rol=SimpleNamespace(codigo="CAJA", activo=True), usuario=SimpleNamespace(activo=True),
        is_active=True, must_change_password=False)
    with pytest.raises(HTTPException) as error:
        _ensure_exchange_admin(actor)
    assert error.value.status_code == 403
