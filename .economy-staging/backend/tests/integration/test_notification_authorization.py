"""Real JWT, account checks, Casbin and PostgreSQL; no auth bypass fixtures."""

from pathlib import Path
from uuid import uuid4

import casbin
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session


def test_real_jwt_and_recipient_ownership_with_explicit_supervision(pg_cluster, synthetic_recipient):
    from app.api.routers.notifications import router
    from app.core.database import get_db
    from app.core.security import create_access_token
    from app.deps.auth import get_enforcer

    security = Path(__file__).resolve().parents[2] / 'app' / 'security'
    enforcer = casbin.Enforcer(str(security / 'model.conf'), str(security / 'policy.csv'))
    with pg_cluster.engine.connect() as connection:
        role_code = connection.execute(text('SELECT codigo FROM roles WHERE id=:id'),
                                       {'id': synthetic_recipient.role_id}).scalar_one()
    for permission in ('notifications:list', 'notifications:view'):
        enforcer.add_policy(role_code, permission, 'use')
    application = FastAPI()
    application.include_router(router, prefix='/notificaciones')

    def test_session():
        with Session(pg_cluster.engine) as session:
            yield session

    application.dependency_overrides[get_db] = test_session
    application.dependency_overrides[get_enforcer] = lambda: enforcer
    token = create_access_token(subject=str(synthetic_recipient.account_id), role_code=role_code)
    headers = {'Authorization': 'Bearer ' + token}
    foreign_user = None
    try:
        with pg_cluster.engine.begin() as connection:
            foreign_user = connection.execute(text('''
                INSERT INTO usuarios(nombres,apellido_paterno,ci,celular,correo,zona,activo)
                VALUES('QA','AJENO',:ci,'00000000',:email,'TEST',true) RETURNING id
            '''), {'ci': uuid4().hex[:25], 'email': uuid4().hex + '@example.invalid'}).scalar_one()
            foreign_id = connection.execute(text('''
                INSERT INTO notificacion(usu_id,not_tipo,not_titulo,not_mensaje,not_fec,not_revision_fecha)
                VALUES(:user,'SISTEMA','QA','SOLO TEST',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP) RETURNING not_id
            '''), {'user': foreign_user}).scalar_one()
        with TestClient(application) as client:
            assert client.get('/notificaciones').status_code == 401
            assert client.get('/notificaciones', headers={'Authorization': 'Bearer invalid'}).status_code == 401
            personal = client.get('/notificaciones', headers=headers, params={'user_id': foreign_user})
            assert personal.status_code == 200 and personal.json()['total'] == 0
            assert client.get(f'/notificaciones/{foreign_id}', headers=headers).status_code == 404
            assert client.get('/notificaciones/supervision', headers=headers).status_code == 403
            enforcer.add_policy(role_code, 'notifications:list_all', 'use')
            supervision = client.get('/notificaciones/supervision', headers=headers, params={'user_id': foreign_user})
            assert supervision.status_code == 200
            assert [row['id'] for row in supervision.json()['items']] == [foreign_id]
            with pg_cluster.engine.begin() as connection:
                connection.execute(text('UPDATE cuentas SET is_active=false WHERE id=:id'),
                                   {'id': synthetic_recipient.account_id})
            assert client.get('/notificaciones', headers=headers).status_code == 403
    finally:
        with pg_cluster.engine.begin() as connection:
            pg_cluster.assert_identity(connection, pg_cluster.manifest)
            connection.execute(text('UPDATE cuentas SET is_active=true WHERE id=:id'), {'id': synthetic_recipient.account_id})
            # ACCESS_DENIED auditing references the synthetic actor via FK.
            connection.execute(text('DELETE FROM auditoria_sistema WHERE usu_id=:id'), {'id': synthetic_recipient.user_id})
            if foreign_user is not None:
                connection.execute(text('DELETE FROM notificacion WHERE usu_id=:id'), {'id': foreign_user})
                connection.execute(text('DELETE FROM usuarios WHERE id=:id'), {'id': foreign_user})
