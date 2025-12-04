from typing import Generator

from sqlalchemy.orm import Session

from app.db.session import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """
    Dependencia para obtener una sesión de base de datos por request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
