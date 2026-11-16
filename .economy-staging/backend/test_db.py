import sys
import logging
from app.core.database import SessionLocal
from app.models.role import Rol

def test_db():
    db = SessionLocal()
    try:
        print("Connected to DB.")
        roles = db.query(Rol).all()
        print(f"Roles found: {len(roles)}")
        for r in roles:
            print(f"- {r.codigo}: {r.nombre}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == '__main__':
    test_db()
