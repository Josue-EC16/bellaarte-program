from app.core.permissions import build_permissions_for_role, build_policy_lines
from app.core.security import ACCESS_TOKEN_TYPE, create_access_token, decode_token, hash_password, verify_password


def test_password_hash_roundtrip() -> None:
    raw_password = "Bellaarte123!"
    hashed = hash_password(raw_password)
    assert verify_password(raw_password, hashed) is True


def test_access_token_contains_subject() -> None:
    token = create_access_token(subject="15", role_code="ADMIN")
    payload = decode_token(token, ACCESS_TOKEN_TYPE)
    assert payload["sub"] == "15"
    assert payload["role"] == "ADMIN"


def test_admin_permissions_include_user_management() -> None:
    permissions = build_permissions_for_role("ADMIN")
    assert "users:create" in permissions
    assert "dashboard:view" in permissions


def test_policy_lines_include_new_report_permissions() -> None:
    lines = build_policy_lines()
    assert "p, ADMIN, clients_reports:view, use" in lines
    assert "p, ADMIN, boutique_reports:view, use" in lines
    assert "p, ADMIN, flete_reports:view, use" in lines
    assert "p, ADMIN, workshop_reports:view, use" in lines
    assert "p, ADMIN, currency_reports:view, use" in lines
