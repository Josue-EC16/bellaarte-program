from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
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


def seed_admin_account(db: Session) -> None:
    admin_role = db.execute(select(Rol).where(Rol.codigo == "ADMIN")).scalar_one()
    existing_account = db.execute(
        select(Cuenta).where(Cuenta.username == settings.bootstrap_admin_username)
    ).scalar_one_or_none()
    if existing_account:
        return

    admin_user = Usuario(
        nombres=settings.bootstrap_admin_names,
        apellido_paterno=settings.bootstrap_admin_last_name,
        apellido_materno=settings.bootstrap_admin_mother_last_name,
        ci=settings.bootstrap_admin_ci,
        celular=settings.bootstrap_admin_cellphone,
        correo=settings.bootstrap_admin_email,
        zona=settings.bootstrap_admin_zone,
        direccion=settings.bootstrap_admin_address,
        activo=True,
    )
    db.add(admin_user)
    db.flush()

    admin_account = Cuenta(
        usuario_id=admin_user.id,
        rol_id=admin_role.id,
        username=settings.bootstrap_admin_username,
        password_hash=hash_password(settings.bootstrap_admin_password),
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
    seed_admin_account(db)
    seed_boutique_types(db)
    admin_account = db.execute(
        select(Cuenta).where(Cuenta.username == settings.bootstrap_admin_username)
    ).scalar_one()
    seed_default_currency(db, admin_account=admin_account)
    seed_receipt_types(db)
