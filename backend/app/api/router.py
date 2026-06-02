from pathlib import Path

import casbin
from fastapi import APIRouter

from app.api.routers import auth, boutique, clients, currencies, fletes, notifications, orders, receipts, roles, users, workshop


security_dir = Path(__file__).resolve().parents[1] / "security"
enforcer = casbin.Enforcer(str(security_dir / "model.conf"), str(security_dir / "policy.csv"))

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(roles.router, prefix="/roles", tags=["roles"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(boutique.router, prefix="/boutique", tags=["boutique"])
api_router.include_router(clients.router, prefix="/clientes", tags=["clientes"])
api_router.include_router(currencies.router, prefix="/monedas", tags=["monedas"])
api_router.include_router(fletes.router, prefix="/fletes", tags=["fletes"])
api_router.include_router(workshop.router, prefix="/taller", tags=["taller"])
api_router.include_router(orders.router, prefix="/pedidos", tags=["pedidos"])
api_router.include_router(receipts.router, prefix="/comprobantes", tags=["comprobantes"])
api_router.include_router(notifications.router, prefix="/notificaciones", tags=["notificaciones"])
