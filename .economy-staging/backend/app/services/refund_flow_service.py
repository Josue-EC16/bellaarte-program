"""Independent money, operative and custody coordinators; one atomic transaction."""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import func, select

from app.core.audit import register_audit_event
from app.models.boutique_enums import EstadoPedidoGeneralEnum, EstadoVentaBoutiqueEnum, TipoEgresoEnum
from app.models.economy import ConstanciaDevolucion, MovimientoEconomico
from app.schemas.economy import RefundFlowRequest, RefundFlowResponse
from app.services.boutique_sale_service import _apply_boutique_sale_state_change
from app.services.economic_ledger_service import lock_active_cut, record_guarantee
from app.services.expense_service import create_expense_record
from app.services.financial_source_service import (
    lock_financial_source, money, recalculate_order_amounts, source_refund_summary,
)
from app.services.flete_service import _apply_flete_output_annulment
from app.services.order_payment_service import _apply_order_payment_annulment
from app.services.notification_service import sync_order_delivery_notifications_for_order


def _state(source, origin_type):
    value = source.estado_salida if origin_type == "SALIDA_FLETE" else source.estado
    return value.value


def _audit(db, account, action, description, reference, ip_address, user_agent):
    register_audit_event(db, action=action, description=description, account=account,
                         user=account.usuario, reference=str(reference),
                         ip_address=ip_address, user_agent=user_agent)


def apply_refund_flow(db, *, payload: RefundFlowRequest, account, ip_address=None,
                      user_agent=None, commit=True) -> RefundFlowResponse:
    try:
        if payload.target_state is not None:
            raise HTTPException(status_code=422, detail="La devolución monetaria no cambia estados. Usa la cancelación operativa separada.")
        cut = lock_active_cut(db, account)
        source = lock_financial_source(db, origin_type=payload.origin_type,
                                      origin_id=payload.origin_id, account=account, cut=cut)
        if payload.origin_type == "PAGO_PEDIDO" and source.pedido.estado_general == EstadoPedidoGeneralEnum.ENTREGADO:
            raise HTTPException(status_code=409, detail="Las devoluciones de pedidos entregados requieren un flujo posterior expresamente aprobado.")
        summary = source_refund_summary(db, payload.origin_type, source)
        amount = money(payload.refund_amount)
        if amount <= 0 or amount > summary["refundable"]:
            raise HTTPException(status_code=409, detail="El monto debe ser positivo y no superar el saldo reembolsable histórico.")
        expense = create_expense_record(
            db, account=account, tipo=TipoEgresoEnum.DEVOLUCION, concepto=payload.concepto,
            cantidad=1, precio_unidad=amount, metodo_pago=payload.payment_method,
            beneficiario=payload.beneficiario, observaciones_1=payload.observaciones,
            observaciones_2=payload.reason, tabla_referencia=payload.origin_type.lower(),
            id_referencia=payload.origin_id,
        )
        remaining = money(summary["refundable"] - amount)
        constancia = ConstanciaDevolucion(egreso_id=expense.id, actor_id=account.usuario_id,
            snapshot={"document_type": "CONSTANCIA_INTERNA_DEVOLUCION", "fiscal": False,
                      "origin_type": payload.origin_type, "origin_id": source.id,
                      "original_receipt_id": source.comprobante.id if source.comprobante else None,
                      "expense_id": expense.id, "amount_bob": str(amount), "currency": "BOB",
                      "payment_method": payload.payment_method.value,
                      "responsible_id": account.usuario_id, "responsible": account.usuario.nombre_completo,
                      "reason": payload.reason, "beneficiary": payload.beneficiario,
                      "refunded_total_bob": str(summary["refunded"] + amount),
                      "refundable_balance_bob": str(remaining)})
        db.add(constancia)
        db.flush()
        if payload.origin_type == "PAGO_PEDIDO":
            recalculate_order_amounts(db, source.pedido)
            sync_order_delivery_notifications_for_order(db, order_id=source.pedido_id)
        _audit(db, account, "ECONOMY_REFUND_RECORDED",
               f"Devolución {payload.origin_type} #{source.id} por {amount} BOB; medio {payload.payment_method.value}.",
               expense.id, ip_address, user_agent)
        response = RefundFlowResponse(origin_type=payload.origin_type, origin_id=source.id,
            target_state=None, refund_amount_bob=amount, expense_id=expense.id,
            expense_amount_bob=expense.monto, origin_state=_state(source, payload.origin_type),
            constancia_id=constancia.id, refundable_balance_bob=remaining)
        if commit:
            db.commit()
        return response
    except Exception:
        db.rollback()
        raise


def apply_operative_cancellation(db, *, payload, account, ip_address=None, user_agent=None, commit=True):
    try:
        cut = lock_active_cut(db, account)
        source = lock_financial_source(db, origin_type=payload.origin_type,
                                      origin_id=payload.origin_id, account=account, cut=cut)
        if payload.origin_type == "VENTA_BOUTIQUE":
            state = EstadoVentaBoutiqueEnum.__members__.get(payload.target_state.upper())
            if state not in {EstadoVentaBoutiqueEnum.CANCELADA, EstadoVentaBoutiqueEnum.ANULADA}:
                raise HTTPException(status_code=422, detail="Estado de cancelación inválido.")
            _apply_boutique_sale_state_change(db, sale=source, target_state=state, reason=payload.reason,
                changed_by=account, ip_address=ip_address, user_agent=user_agent)
        elif payload.origin_type == "PAGO_PEDIDO":
            if payload.target_state.upper() != "ANULADA":
                raise HTTPException(status_code=422, detail="Estado de anulación inválido.")
            if source.pedido.estado_general == EstadoPedidoGeneralEnum.ENTREGADO:
                raise HTTPException(status_code=409, detail="No puedes anular pagos de pedidos entregados.")
            _apply_order_payment_annulment(db, payment=source, reason=payload.reason,
                annulled_by=account, ip_address=ip_address, user_agent=user_agent)
        else:
            if payload.target_state.upper() != "ANULADA":
                raise HTTPException(status_code=422, detail="Estado de anulación inválido.")
            _apply_flete_output_annulment(db, salida=source, motivo=payload.reason,
                changed_by=account, ip_address=ip_address, user_agent=user_agent)
        summary = source_refund_summary(db, payload.origin_type, source)
        response = {"origin_type": payload.origin_type, "origin_id": source.id,
                    "origin_state": _state(source, payload.origin_type),
                    "pending_refund_bob": float(summary["pending"]), "money_returned_bob": 0}
        if commit:
            db.commit()
        return response
    except Exception:
        db.rollback()
        raise


def apply_guarantee_movement(db, *, origin_id: int, payload, account, ip_address=None,
                             user_agent=None, commit=True):
    try:
        cut = lock_active_cut(db, account)
        source = lock_financial_source(db, origin_type="SALIDA_FLETE", origin_id=origin_id,
                                      account=account, cut=cut)
        action = payload.action.lower()
        if action == "retain" and (account.rol.codigo != "ADMIN" or not payload.reason):
            raise HTTPException(status_code=403, detail="La retención de garantía exige ADMIN y una justificación.")
        totals = dict(db.execute(select(MovimientoEconomico.evento,
                           func.sum(MovimientoEconomico.monto_bob)).where(
            MovimientoEconomico.salida_flete_id == source.id,
            MovimientoEconomico.evento.in_(["garantia_recibida", "garantia_devuelta", "garantia_retenida"]),
        ).group_by(MovimientoEconomico.evento)).all())
        received = money(totals.get("garantia_recibida"))
        returned = money(totals.get("garantia_devuelta"))
        retained = money(totals.get("garantia_retenida"))
        amount = money(payload.amount)
        if action == "receive":
            available = money(source.garantia) - received
        else:
            available = received - returned - retained
        if amount <= 0 or amount > available:
            raise HTTPException(status_code=409, detail="El movimiento supera la garantía disponible y verificable.")
        if action not in {"receive", "return", "retain"}:
            raise HTTPException(status_code=422, detail="Movimiento de garantía inválido.")
        record_guarantee(db, account=account, cut=cut, source=source, action=action,
                         amount=amount, payment_method=payload.payment_method, reason=payload.reason)
        if action == "return":
            source.garantia_devuelta = returned + amount
        _audit(db, account, "ECONOMY_GUARANTEE_MOVED",
               f"Custodia flete #{source.id}: {action} por {amount} BOB ({payload.payment_method.value}).",
               source.id, ip_address, user_agent)
        db.flush()
        response = {"origin_id": source.id, "action": payload.action, "amount_bob": float(amount),
                    "commercial_income_bob": 0, "remaining_available_bob": float(available - amount)}
        if commit:
            db.commit()
        return response
    except Exception:
        db.rollback()
        raise
