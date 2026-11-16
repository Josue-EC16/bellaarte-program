from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.core.user_validation import generate_temporary_password
from app.schemas.auth import ChangePasswordRequest, CreateUserRequest, LoginRequest, ResetPasswordRequest, UpdateUserRequest
from app.services.user_service import _protect_account_change


def identity(**changes):
    return dict(nombres="  María   José  ", apellido_paterno="  Pérez ", ci="0012345",
                celular="70000000", correo="maria@example.com", zona=" Villa   Fátima ",
                role_code="MODISTA", **changes)


def test_normalized_identity_generates_actual_initials_and_preserves_ci_zeroes():
    user = CreateUserRequest(**identity())
    assert user.nombres == "MARÍA JOSÉ"
    assert user.apellido_paterno == "PÉREZ"
    assert user.zona == "VILLA FÁTIMA"
    assert generate_temporary_password(user) == "MP0012345"
    assert CreateUserRequest(**identity(), apellido_materno="   ", direccion="  ").apellido_materno is None


@pytest.mark.parametrize("field,value", [
    ("nombres", "   "), ("apellido_paterno", "\u200b\u200b"), ("zona", "\u00a0\t"),
    ("nombres", "A\u200bNA"), ("apellido_paterno", "12"), ("ci", "123456"),
    ("nombres", "\u0301ANA"), ("apellido_paterno", "PEREZ \u0301LOPEZ"),
    ("ci", "1234567A"), ("ci", " 1234567"), ("ci", "１２３４５６７"),
    ("celular", "        "), ("role_code", "   "), ("correo", "   "),
])
def test_create_and_edit_reject_invalid_required_identity(field, value):
    data = identity()
    data[field] = value
    for contract in (CreateUserRequest, UpdateUserRequest):
        with pytest.raises(ValidationError) as error:
            contract(**data)
        assert any(item["loc"] == (field,) for item in error.value.errors())


def test_reset_accepts_the_ui_body_and_rejects_client_chosen_credentials():
    assert ResetPasswordRequest.model_validate({}).model_dump() == {}
    with pytest.raises(ValidationError):
        ResetPasswordRequest(temporary_password="ClientChosen123!")


@pytest.mark.parametrize("password", ["ClaveNueva1!\x00", "ClaveNueva1!\n", "ClaveNueva1!" + "é" * 50])
def test_personal_password_rejects_controls_and_bcrypt_overflow_as_field_errors(password):
    with pytest.raises(ValidationError) as error:
        ChangePasswordRequest(current_password="ClaveActual1!", new_password=password)
    assert error.value.errors()[0]["loc"] == ("new_password",)


@pytest.mark.parametrize("username", ["   ", "\u200badmin", "\t\n"])
def test_login_does_not_accept_blank_or_invisible_usernames(username):
    with pytest.raises(ValidationError):
        LoginRequest(username=username, password="ClaveActual1!")


@pytest.mark.parametrize("user_active,account_active", [(False, True), (True, False), (False, False)])
def test_admin_cannot_disable_self_through_either_edit_state(user_active, account_active):
    account = SimpleNamespace(id=7, rol_id=1)
    with pytest.raises(HTTPException) as error:
        _protect_account_change(Mock(), actor=account, target=account,
            role=SimpleNamespace(id=1, codigo="ADMIN", activo=True),
            user_active=user_active, account_active=account_active)
    assert error.value.status_code == 409


def test_admin_cannot_demote_self_even_if_other_administrators_exist():
    account = SimpleNamespace(id=7, rol_id=1)
    with pytest.raises(HTTPException) as error:
        _protect_account_change(Mock(), actor=account, target=account,
            role=SimpleNamespace(id=2, codigo="CAJA", activo=True), user_active=True, account_active=True)
    assert error.value.status_code == 409


def test_last_enabled_administrator_must_survive_a_change():
    database = Mock()
    database.execute.return_value.scalar_one_or_none.return_value = None
    with pytest.raises(HTTPException) as error:
        _protect_account_change(database, actor=SimpleNamespace(id=7), target=SimpleNamespace(id=8),
            role=SimpleNamespace(id=2, codigo="CAJA", activo=True), user_active=True, account_active=True)
    assert error.value.status_code == 409


def test_admin_can_change_another_admin_when_a_usable_admin_remains():
    database = Mock()
    database.execute.return_value.scalar_one_or_none.return_value = 7
    _protect_account_change(database, actor=SimpleNamespace(id=7), target=SimpleNamespace(id=8),
        role=SimpleNamespace(id=2, codigo="CAJA", activo=True), user_active=True, account_active=True)
