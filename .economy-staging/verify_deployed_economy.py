"""Post-deployment service smoke: enforced read-only business transaction."""
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
os.chdir(BACKEND)
sys.path.insert(0, str(BACKEND))

from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.account import Cuenta
from app.models.role import Rol
from app.models.economy import CorteCaja
from app.services.income_service import list_income_rows, get_income_refund_context
from app.services.expense_service import list_expenses
from app.services.cash_cut_service import list_cash_cuts, get_cash_cut_detail, get_my_active_cut, get_my_cut_history_page
from app.services.economy_report_service import get_income_statement_report, get_cash_flow_report, get_my_period_report, get_cashier_report
from app.services.currency_service import list_currencies

url = make_url(settings.effective_database_url)
assert url.host in {"localhost", "127.0.0.1"} and (url.port or 5432) == 5432 and url.database == "bellaarte_db"
engine = create_engine(url, connect_args={"options": "-c default_transaction_read_only=on -c statement_timeout=15000"})
with engine.connect() as connection:
    with Session(connection, autoflush=False) as db:
        assert db.scalar(text("SHOW transaction_read_only")) == "on"
        admin = db.scalar(select(Cuenta).join(Cuenta.rol).where(Rol.codigo == "ADMIN").order_by(Cuenta.id).limit(1))
        assert admin is not None
        income = list_income_rows(db, account=admin)
        expenses = list_expenses(db, account=admin)
        cuts = list_cash_cuts(db, account=admin)
        statement = get_income_statement_report(db, account=admin)
        flow = get_cash_flow_report(db, account=admin)
        assert statement.resultado_bob == flow.flujo_neto_bob
        for method in ("efectivo", "qr", "transaccion", "tarjeta", "ticket_o_vale"):
            list_income_rows(db, account=admin, payment_method=method)
            filtered = get_income_statement_report(db, account=admin, payment_method=method)
            assert filtered.resultado_bob is None and not filtered.comparable
        for source in ("VENTA_BOUTIQUE", "PAGO_PEDIDO", "SALIDA_FLETE"):
            page = list_income_rows(db, account=admin, source_type=source)
            if page.items:
                get_income_refund_context(db, account=admin, origin_type=source, origin_id=page.items[0].source_id)
        for cut in cuts.items:
            get_cash_cut_detail(db, cut_id=cut.id, account=admin)
            get_cashier_report(db, account=admin, cashier_user_id=cut.cajero.id)
        list_currencies(db)
        cashier = db.scalar(select(Cuenta).join(Cuenta.rol).where(Rol.codigo == "CAJA").order_by(Cuenta.id).limit(1))
        if cashier is not None:
            get_my_active_cut(db, account=cashier)
            get_my_cut_history_page(db, account=cashier)
            get_my_period_report(db, account=cashier)
            list_income_rows(db, account=cashier)
            list_expenses(db, account=cashier)
        db.rollback()
print("Read-only business smoke passed: ADMIN/CAJA scopes, three sources, five enum filters, cuts, reports and currency reference.")
engine.dispose()
