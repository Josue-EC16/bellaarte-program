from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.audit import register_audit_event
from app.models.account import Cuenta
from app.models.boutique_enums import EstadoVentaBoutiqueEnum, TipoEgresoEnum
from app.schemas.economy import RefundFlowRequest, RefundFlowResponse
from app.services.boutique_sale_service import _apply_boutique_sale_state_change, _get_sale_entity
from app.services.expense_service import create_expense_record
from app.services.flete_service import _apply_flete_output_annulment, _get_output_entity
from app.services.income_service import get_income_refund_context, validate_refund_target_state
from app.services.order_payment_service import _apply_order_payment_annulment, _get_payment_entity


def apply_refund_flow(
    db: Session,
    *,
    payload: RefundFlowRequest,
    account: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> RefundFlowResponse:
    validate_refund_target_state(origin_type=payload.origin_type, target_state=payload.target_state)
    context = get_income_refund_context(
        db,
        origin_type=payload.origin_type,
        origin_id=payload.origin_id,
    )
    if payload.refund_amount > context.refundable_balance_bob:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El monto de devolución supera el saldo reembolsable disponible para este ingreso.",
        )

    table_ref = payload.origin_type.lower()
    expense = create_expense_record(
        db,
        account=account,
        tipo=TipoEgresoEnum.DEVOLUCION,
        concepto=payload.concepto,
        cantidad=1,
        precio_unidad=payload.refund_amount,
        beneficiario=payload.beneficiario,
        observaciones_1=payload.observaciones,
        observaciones_2=payload.reason,
        tabla_referencia=table_ref,
        id_referencia=payload.origin_id,
    )

    if payload.origin_type == "VENTA_BOUTIQUE":
        sale = _get_sale_entity(db, payload.origin_id)
        target_state = (
            EstadoVentaBoutiqueEnum.CANCELADA
            if payload.target_state == "CANCELADA"
            else EstadoVentaBoutiqueEnum.ANULADA
        )
        _apply_boutique_sale_state_change(
            db,
            sale=sale,
            target_state=target_state,
            reason=payload.reason,
            changed_by=account,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    elif payload.origin_type == "PAGO_PEDIDO":
        payment = _get_payment_entity(db, payload.origin_id)
        _apply_order_payment_annulment(
            db,
            payment=payment,
            reason=payload.reason,
            annulled_by=account,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    else:
        salida = _get_output_entity(db, payload.origin_id)
        _apply_flete_output_annulment(
            db,
            salida=salida,
            motivo=payload.reason,
            changed_by=account,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    register_audit_event(
        db,
        action="ECONOMY_REFUND_RECORDED",
        description=(
            f"SE REGISTRÓ LA DEVOLUCIÓN ECONÓMICA DEL ORIGEN '{payload.origin_type}' "
            f"#{payload.origin_id} POR {payload.refund_amount:.2f} BS."
        ),
        account=account,
        user=account.usuario,
        reference=str(expense.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return RefundFlowResponse(
        origin_type=payload.origin_type,
        origin_id=payload.origin_id,
        target_state=payload.target_state,
        refund_amount_bob=payload.refund_amount,
        expense_id=expense.id,
        expense_amount_bob=float(expense.monto),
        origin_state=payload.target_state,
    )
