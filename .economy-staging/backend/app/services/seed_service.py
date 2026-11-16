from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.permissions import build_policy_lines
from app.core.security import hash_password
from app.models.account import Cuenta
from app.models.receipt import TipoComprobante
from app.models.role import Rol
from app.models.user import Usuario
from app.services.boutique_service import seed_boutique_types
from app.services.currency_service import seed_default_currency


ROLE_SEED = (
    ("ADMIN", "ADMIN", "Acceso total al modulo inicial de seguridad."),
    ("INV_TALLER", "ENCARGADA(O) DEL INVENTARIO TALLER", "Gestion operativa del inventario del taller."),
    ("INV_BOUTIQUE", "ENCARGADA(O) DEL INVENTARIO BOUTIQUE", "Gestion operativa del inventario boutique."),
    ("CAJA", "CAJERA(O)", "Registro de cobros y validacion de operaciones."),
    ("MODISTA", "MODISTA", "Consulta operativa del sistema para produccion."),
)


def seed_roles(db: Session) -> None:
    existing = {role.codigo for role in db.execute(select(Rol)).scalars().all()}
    for codigo, nombre, descripcion in ROLE_SEED:
        if codigo in existing:
            continue
        db.add(Rol(codigo=codigo, nombre=nombre, descripcion=descripcion, activo=True))
    db.commit()


def ensure_policy_files() -> None:
    base_path = Path(__file__).resolve().parents[1] / "security"
    model_path = base_path / "model.conf"
    policy_path = base_path / "policy.csv"
    if not model_path.exists() or not policy_path.exists():
        raise RuntimeError("No se encontraron los archivos base de Casbin.")


def sync_policy_file() -> None:
    base_path = Path(__file__).resolve().parents[1] / "security"
    policy_path = base_path / "policy.csv"
    lines = build_policy_lines()
    content = "\n".join(lines) + "\n"
    current_content = policy_path.read_text(encoding="utf-8") if policy_path.exists() else None
    if current_content != content:
        policy_path.write_text(content, encoding="utf-8")


def seed_admin_account(db: Session) -> None:
    seed_named_admin_account(
        db,
        username=settings.bootstrap_admin_username,
        password=settings.bootstrap_admin_password,
        email=settings.bootstrap_admin_email,
        names=settings.bootstrap_admin_names,
        last_name=settings.bootstrap_admin_last_name,
        mother_last_name=settings.bootstrap_admin_mother_last_name,
        ci=settings.bootstrap_admin_ci,
        cellphone=settings.bootstrap_admin_cellphone,
        zone=settings.bootstrap_admin_zone,
        address=settings.bootstrap_admin_address,
    )


def seed_admin2_account(db: Session) -> None:
    seed_named_admin_account(
        db,
        username=settings.bootstrap_admin2_username,
        password=settings.bootstrap_admin2_password,
        email=settings.bootstrap_admin2_email,
        names=settings.bootstrap_admin2_names,
        last_name=settings.bootstrap_admin2_last_name,
        mother_last_name=settings.bootstrap_admin2_mother_last_name,
        ci=settings.bootstrap_admin2_ci,
        cellphone=settings.bootstrap_admin2_cellphone,
        zone=settings.bootstrap_admin2_zone,
        address=settings.bootstrap_admin2_address,
    )


def seed_named_admin_account(
    db: Session,
    *,
    username: str,
    password: str,
    email: str,
    names: str,
    last_name: str,
    mother_last_name: str,
    ci: str,
    cellphone: str,
    zone: str,
    address: str,
) -> None:
    admin_role = db.execute(select(Rol).where(Rol.codigo == "ADMIN")).scalar_one()
    existing_account = db.execute(select(Cuenta).where(Cuenta.username == username)).scalar_one_or_none()
    if existing_account is not None:
        existing_account.rol_id = admin_role.id
        existing_account.password_hash = hash_password(password)
        existing_account.must_change_password = True
        existing_account.is_active = True
        if existing_account.usuario is not None:
            existing_account.usuario.activo = True
        db.commit()
        return

    existing_user = db.execute(select(Usuario).where(Usuario.correo == email)).scalar_one_or_none()
    if existing_user is None:
        existing_user = Usuario(
            nombres=names,
            apellido_paterno=last_name,
            apellido_materno=mother_last_name,
            ci=ci,
            celular=cellphone,
            correo=email,
            zona=zone,
            direccion=address,
            activo=True,
        )
        db.add(existing_user)
        db.flush()
    else:
        existing_user.nombres = names
        existing_user.apellido_paterno = last_name
        existing_user.apellido_materno = mother_last_name
        existing_user.ci = ci
        existing_user.celular = cellphone
        existing_user.zona = zone
        existing_user.direccion = address
        existing_user.activo = True

    admin_account = Cuenta(
        usuario_id=existing_user.id,
        rol_id=admin_role.id,
        username=username,
        password_hash=hash_password(password),
        must_change_password=True,
        is_active=True,
    )
    db.add(admin_account)
    db.commit()


def seed_receipt_types(db: Session) -> None:
    expected_types = (
        ("VENTA_BOUTIQUE_INTERNO", "COMPROBANTE INTERNO PARA VENTAS BOUTIQUE"),
        ("PAGO_PEDIDO_INTERNO", "COMPROBANTE INTERNO PARA PAGOS DE PEDIDO"),
        ("FLETE_INTERNO", "COMPROBANTE INTERNO PARA OPERACIONES DE FLETE"),
    )
    existing = {
        receipt_type.nombre: receipt_type
        for receipt_type in db.execute(select(TipoComprobante)).scalars().all()
    }
    for name, description in expected_types:
        current = existing.get(name)
        if current is None:
            db.add(
                TipoComprobante(
                    nombre=name,
                    descripcion=description,
                    es_fiscal=False,
                    habilitado=True,
                )
            )
            continue
        current.descripcion = description
        current.es_fiscal = False
        current.habilitado = True
    db.commit()


def seed_security(db: Session) -> None:
    seed_roles(db)
    ensure_policy_files()
    sync_policy_file()
    seed_admin_account(db)
    seed_boutique_types(db)
    admin_account = db.execute(
        select(Cuenta).where(Cuenta.username == settings.bootstrap_admin_username)
    ).scalar_one()
    seed_default_currency(db, admin_account=admin_account)
    seed_receipt_types(db)
