from pathlib import Path

import casbin
from fastapi import APIRouter

from app.api.routers import auth, roles, users


security_dir = Path(__file__).resolve().parents[1] / "security"
enforcer = casbin.Enforcer(str(security_dir / "model.conf"), str(security_dir / "policy.csv"))

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(roles.router, prefix="/roles", tags=["roles"])
api_router.include_router(users.router, prefix="/users", tags=["users"])

