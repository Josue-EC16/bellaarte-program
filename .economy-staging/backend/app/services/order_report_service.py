from datetime import date, timedelta
from html import escape
from collections import defaultdict

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.boutique_enums import EstadoPagoPedidoEnum, EstadoPedidoGeneralEnum, PruebaEstadoPedidoEnum
from app.models.client import Cliente
from app.models.currency import Moneda
from app.models.user import Usuario
from app.models.order import PagoPedido, Pedido, PruebaPedido
from app.schemas.order import ClientOrderSummaryReport, OrderBalanceReportItem
from app.services.order_payment_service import list_order_payments
from app.services.order_service import _to_client_summary, _to_list_item
from app.services.order_test_service import list_order_tests
from app.services.economy_query_service import apply_dates, refund_totals_query
from app.services.financial_source_service import order_financial_summary


def get_client_order_summary(db: Session, client_id: int) -> ClientOrderSummaryReport:
    client = db.execute(select(Cliente).where(Cliente.id == client_id)).scalar_one_or_none()
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado.")
    orders = db.execute(select(Pedido).options(joinedload(Pedido.cliente)).where(Pedido.cliente_id == client.id)).unique().scalars().all()
    active_orders = [order for order in orders if order.estado_general == EstadoPedidoGeneralEnum.ACTIVO and order.habilitado]
    financial={order.id:order_financial_summary(db,order) for order in active_orders}
    return ClientOrderSummaryReport(
        client=_to_client_summary(client),
        total_contratado=sum(float(order.precio_total or 0) for order in active_orders),
        total_pagado=sum(float(financial[order.id]["total_pagado"]) for order in active_orders),
        saldo_pendiente=sum(float(financial[order.id]["saldo_exigible_bob"]) for order in active_orders),
        pedidos_activos=sum(1 for order in orders if order.estado_general == EstadoPedidoGeneralEnum.ACTIVO and order.habilitado),
        pedidos_inactivos=sum(1 for order in orders if order.estado_general == EstadoPedidoGeneralEnum.INACTIVO or not order.habilitado),
        pedidos_entregados=sum(1 for order in orders if order.estado_general == EstadoPedidoGeneralEnum.ENTREGADO),
        pedidos_cancelados=sum(1 for order in orders if order.estado_general == EstadoPedidoGeneralEnum.CANCELADO),
        orders=[_to_list_item(order,db) for order in orders],
        payments=list_order_payments(db, client_id=client.id),
    )


def list_order_balance_report(db: Session) -> list[OrderBalanceReportItem]:
    refunds=refund_totals_query()
    paid=select(PagoPedido.pedido_id.label("order_id"),func.sum(PagoPedido.monto_bob-func.coalesce(refunds.c.refunded,0)).label("paid"))\
        .outerjoin(refunds,(refunds.c.origin=="pago_pedido")&(refunds.c.source_id==PagoPedido.id)).group_by(PagoPedido.pedido_id).subquery()
    rows = db.execute(
        select(
            Cliente.id,
            Cliente.nombres,
            Cliente.apellido_paterno,
            Cliente.apellido_materno,
            func.coalesce(func.sum(Pedido.precio_total), 0),
            func.coalesce(func.sum(paid.c.paid),0),
            func.coalesce(func.sum(func.greatest(0,Pedido.precio_total-func.coalesce(paid.c.paid,0))),0),
            func.count(Pedido.id),
        )
        .join(Pedido, Pedido.cliente_id == Cliente.id)
        .outerjoin(paid,paid.c.order_id==Pedido.id)
        .where(Pedido.estado_general == EstadoPedidoGeneralEnum.ACTIVO, Pedido.habilitado.is_(True))
        .group_by(Cliente.id)
        .order_by(func.sum(Pedido.precio_total-func.coalesce(paid.c.paid,0)).desc())
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
    refunds=refund_totals_query()
    net=PagoPedido.monto_bob-func.coalesce(refunds.c.refunded,0)
    stmt=select(PagoPedido.id.label("id"),PagoPedido.monto_bob.label("gross"),net.label("net"),
        PagoPedido.metodo_pago.label("method"),Moneda.codigo.label("currency"),
        func.concat_ws(" ",Usuario.nombres,Usuario.apellido_paterno,Usuario.apellido_materno).label("user"))\
        .join(Moneda,Moneda.id==PagoPedido.moneda_id).join(Usuario,Usuario.id==PagoPedido.usuario_id)\
        .outerjoin(refunds,(refunds.c.origin=="pago_pedido")&(refunds.c.source_id==PagoPedido.id))
    scope=apply_dates(stmt,PagoPedido.fecha,date_from=date_from,date_to=date_to).subquery()
    gross,paid,count=db.execute(select(func.coalesce(func.sum(scope.c.gross),0),func.coalesce(func.sum(scope.c.net),0),func.count()).select_from(scope)).one()
    def grouped(column):
        return [{"label":getattr(label,"value",label),"total_bob":float(amount)}
                for label,amount in db.execute(select(column,func.sum(scope.c.net)).group_by(column).order_by(column))]
    return {"total_bob":float(paid),"gross_total_bob":float(gross),"refunded_total_bob":float(gross-paid),"count":count,
        "by_method":grouped(scope.c.method),"by_currency":grouped(scope.c.currency),"by_user":grouped(scope.c.user),
        "payments":list_order_payments(db,date_from=date_from,date_to=date_to)}


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
    return [_to_list_item(order,db) for order in db.execute(stmt.order_by(Pedido.fecha_entrega.asc())).unique().scalars().all()]


def build_client_printable_html(db: Session, client_id: int) -> str:
    summary = get_client_order_summary(db, client_id)
    order_rows = "".join(
        f"<tr><td>{escape(order.codigo)}</td><td>{order.tipo.value.upper()}</td><td>{order.estado_general.value.upper()}</td>"
        f"<td>{order.precio_total:.2f}</td><td>{order.total_pagado:.2f}</td><td>{order.saldo:.2f}</td></tr>"
        for order in summary.orders
    )
    payment_rows = "".join(
        f"<tr><td>{payment.fecha:%d/%m/%Y}</td><td>{escape(payment.pedido_codigo)}</td><td>{payment.metodo_pago.value.upper()}</td><td>{payment.monto_bob:.2f}</td><td>{payment.refunded_amount_bob:.2f}</td><td>{payment.effective_amount_bob:.2f}</td></tr>"
        for payment in summary.payments
    )
    return f"""
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <title>Resumen de pedidos - {escape(summary.client.full_name)}</title>
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
  <h2>Cliente: {escape(summary.client.full_name)}</h2>
  <p>Código: {escape(summary.client.codigo)} | Celular: {escape(summary.client.celular or "-")}</p>
  <section class="totals">
    <div class="card"><strong>Total contratado</strong><br />Bs {summary.total_contratado:.2f}</div>
    <div class="card"><strong>Total pagado</strong><br />Bs {summary.total_pagado:.2f}</div>
    <div class="card"><strong>Saldo pendiente</strong><br />Bs {summary.saldo_pendiente:.2f}</div>
  </section>
  <h2>Pedidos</h2>
  <table><thead><tr><th>Código</th><th>Tipo</th><th>Estado</th><th>Total</th><th>Pagado</th><th>Saldo</th></tr></thead><tbody>{order_rows}</tbody></table>
  <h2>Pagos</h2>
  <table><thead><tr><th>Fecha</th><th>Pedido</th><th>Método</th><th>Cobrado bruto Bs</th><th>Devuelto Bs</th><th>Crédito efectivo Bs</th></tr></thead><tbody>{payment_rows}</tbody></table>
</body>
</html>
"""
