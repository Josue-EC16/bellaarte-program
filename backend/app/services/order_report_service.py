from datetime import date, timedelta
from collections import defaultdict

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.boutique_enums import EstadoPagoPedidoEnum, EstadoPedidoGeneralEnum, PruebaEstadoPedidoEnum
from app.models.client import Cliente
from app.models.order import PagoPedido, Pedido, PruebaPedido
from app.schemas.order import ClientOrderSummaryReport, OrderBalanceReportItem
from app.services.order_payment_service import list_order_payments
from app.services.order_service import _to_client_summary, _to_list_item
from app.services.order_test_service import list_order_tests


def get_client_order_summary(db: Session, client_id: int) -> ClientOrderSummaryReport:
    client = db.execute(select(Cliente).where(Cliente.id == client_id)).scalar_one_or_none()
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado.")
    orders = db.execute(select(Pedido).options(joinedload(Pedido.cliente)).where(Pedido.cliente_id == client.id)).unique().scalars().all()
    active_orders = [order for order in orders if order.estado_general == EstadoPedidoGeneralEnum.ACTIVO and order.habilitado]
    return ClientOrderSummaryReport(
        client=_to_client_summary(client),
        total_contratado=sum(float(order.precio_total or 0) for order in active_orders),
        total_pagado=sum(float(order.total_pagado or 0) for order in active_orders),
        saldo_pendiente=sum(float(order.saldo or 0) for order in active_orders),
        pedidos_activos=sum(1 for order in orders if order.estado_general == EstadoPedidoGeneralEnum.ACTIVO and order.habilitado),
        pedidos_inactivos=sum(1 for order in orders if order.estado_general == EstadoPedidoGeneralEnum.INACTIVO or not order.habilitado),
        pedidos_entregados=sum(1 for order in orders if order.estado_general == EstadoPedidoGeneralEnum.ENTREGADO),
        pedidos_cancelados=sum(1 for order in orders if order.estado_general == EstadoPedidoGeneralEnum.CANCELADO),
        orders=[_to_list_item(order) for order in orders],
        payments=list_order_payments(db, client_id=client.id),
    )


def list_order_balance_report(db: Session) -> list[OrderBalanceReportItem]:
    rows = db.execute(
        select(
            Cliente.id,
            Cliente.nombres,
            Cliente.apellido_paterno,
            Cliente.apellido_materno,
            func.coalesce(func.sum(Pedido.precio_total), 0),
            func.coalesce(func.sum(Pedido.total_pagado), 0),
            func.coalesce(func.sum(Pedido.saldo), 0),
            func.count(Pedido.id),
        )
        .join(Pedido, Pedido.cliente_id == Cliente.id)
        .where(Pedido.estado_general == EstadoPedidoGeneralEnum.ACTIVO, Pedido.habilitado.is_(True))
        .group_by(Cliente.id)
        .order_by(func.sum(Pedido.saldo).desc())
    ).all()
    return [
        OrderBalanceReportItem(
            client_id=row[0],
            client_name=" ".join(part for part in [row[1], row[2], row[3]] if part),
            total_contratado=float(row[4] or 0),
            total_pagado=float(row[5] or 0),
            saldo_pendiente=float(row[6] or 0),
            active_orders=row[7],
        )
        for row in rows
    ]


def list_order_payment_report(db: Session, *, date_from: date | None = None, date_to: date | None = None):
    stmt = (
        select(PagoPedido)
        .options(joinedload(PagoPedido.moneda), joinedload(PagoPedido.usuario), joinedload(PagoPedido.pedido).joinedload(Pedido.cliente))
        .where(PagoPedido.estado == EstadoPagoPedidoEnum.REGISTRADO)
    )
    if date_from:
        stmt = stmt.where(func.date(PagoPedido.fecha) >= date_from)
    if date_to:
        stmt = stmt.where(func.date(PagoPedido.fecha) <= date_to)
    rows = db.execute(stmt).scalars().all()
    by_method = defaultdict(float)
    by_currency = defaultdict(float)
    by_user = defaultdict(float)
    for payment in rows:
        by_method[payment.metodo_pago.value.upper()] += float(payment.monto_bob or 0)
        by_currency[payment.moneda.codigo] += float(payment.monto_bob or 0)
        by_user[payment.usuario.nombre_completo] += float(payment.monto_bob or 0)
    return {
        "total_bob": sum(float(payment.monto_bob or 0) for payment in rows),
        "count": len(rows),
        "by_method": [{"label": key, "total_bob": value} for key, value in by_method.items()],
        "by_currency": [{"label": key, "total_bob": value} for key, value in by_currency.items()],
        "by_user": [{"label": key, "total_bob": value} for key, value in by_user.items()],
        "payments": list_order_payments(db, state=EstadoPagoPedidoEnum.REGISTRADO, date_from=date_from, date_to=date_to),
    }


def list_order_test_report(db: Session, *, date_from: date | None = None, date_to: date | None = None):
    today = date.today()
    upcoming = list_order_tests(db, date_from=date_from or today, date_to=date_to or today + timedelta(days=30))
    pending_ready = [item for item in upcoming if item.estado != PruebaEstadoPedidoEnum.LISTO]
    return {
        "today": list_order_tests(db, date_from=today, date_to=today),
        "upcoming": upcoming,
        "pending_or_not_ready": pending_ready,
        "ready_count": sum(1 for item in upcoming if item.estado == PruebaEstadoPedidoEnum.LISTO),
        "late_count": db.execute(select(func.count(PruebaPedido.id)).where(PruebaPedido.fecha < today)).scalar_one(),
    }


def list_order_delivery_report(db: Session, *, date_from: date | None = None, date_to: date | None = None):
    today = date.today()
    stmt = select(Pedido).options(joinedload(Pedido.cliente)).where(Pedido.estado_general == EstadoPedidoGeneralEnum.ACTIVO, Pedido.habilitado.is_(True))
    stmt = stmt.where(Pedido.fecha_entrega >= (date_from or today))
    stmt = stmt.where(Pedido.fecha_entrega <= (date_to or today + timedelta(days=30)))
    return [_to_list_item(order) for order in db.execute(stmt.order_by(Pedido.fecha_entrega.asc())).unique().scalars().all()]


def build_client_printable_html(db: Session, client_id: int) -> str:
    summary = get_client_order_summary(db, client_id)
    order_rows = "".join(
        f"<tr><td>{order.codigo}</td><td>{order.tipo.value.upper()}</td><td>{order.estado_general.value.upper()}</td>"
        f"<td>{order.precio_total:.2f}</td><td>{order.total_pagado:.2f}</td><td>{order.saldo:.2f}</td></tr>"
        for order in summary.orders
    )
    payment_rows = "".join(
        f"<tr><td>{payment.fecha:%d/%m/%Y}</td><td>{payment.pedido_codigo}</td><td>{payment.metodo_pago.value.upper()}</td><td>{payment.monto_bob:.2f}</td></tr>"
        for payment in summary.payments
    )
    return f"""
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <title>Resumen de pedidos - {summary.client.full_name}</title>
  <style>
    body {{ font-family: Arial, sans-serif; color: #2d1a16; margin: 32px; }}
    header {{ display: flex; gap: 16px; align-items: center; border-bottom: 2px solid #8f3d2e; padding-bottom: 16px; }}
    h1, h2 {{ margin: 0 0 8px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
    th {{ background: #8f3d2e; color: white; text-align: left; }}
    th, td {{ border: 1px solid #d8c5bd; padding: 8px; font-size: 12px; }}
    .totals {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 20px 0; }}
    .card {{ border: 1px solid #d8c5bd; border-radius: 10px; padding: 12px; background: #fff8f5; }}
    @media print {{ button {{ display: none; }} body {{ margin: 12mm; }} }}
  </style>
</head>
<body>
  <button onclick="window.print()">Imprimir / guardar PDF</button>
  <header>
    <img src="/logo_bellaarte2.png" alt="BellaArte Boutique" style="width:96px;height:auto" />
    <div>
      <h1>BellaArte Boutique</h1>
      <p>Resumen de pedidos, pagos y saldos por cliente</p>
    </div>
  </header>
  <h2>Cliente: {summary.client.full_name}</h2>
  <p>Código: {summary.client.codigo} | Celular: {summary.client.celular or "-"}</p>
  <section class="totals">
    <div class="card"><strong>Total contratado</strong><br />Bs {summary.total_contratado:.2f}</div>
    <div class="card"><strong>Total pagado</strong><br />Bs {summary.total_pagado:.2f}</div>
    <div class="card"><strong>Saldo pendiente</strong><br />Bs {summary.saldo_pendiente:.2f}</div>
  </section>
  <h2>Pedidos</h2>
  <table><thead><tr><th>Código</th><th>Tipo</th><th>Estado</th><th>Total</th><th>Pagado</th><th>Saldo</th></tr></thead><tbody>{order_rows}</tbody></table>
  <h2>Pagos</h2>
  <table><thead><tr><th>Fecha</th><th>Pedido</th><th>Método</th><th>Monto Bs</th></tr></thead><tbody>{payment_rows}</tbody></table>
</body>
</html>
"""
