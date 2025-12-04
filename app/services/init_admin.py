from sqlalchemy.orm import Session
from app.db.models import User, UserRole
from app.core.security import hash_password


BUILTIN_ADMIN_EMAIL = "admin@library.com"


def ensure_builtin_admin(db: Session):
    admin = db.query(User).filter(User.email == BUILTIN_ADMIN_EMAIL).first()
    if admin:
        return

    admin = User(
        email=BUILTIN_ADMIN_EMAIL,
        full_name="Built-in Admin",
        hashed_password=hash_password("admin123"),  # cámbialo luego
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(admin)
    db.commit()
