from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.dependencies import get_db
from app.api.v1.dependencies_auth import get_current_user, require_role
from app.core.security import hash_password
from app.db.models import User, UserRole
from app.schemas.user import UserRead, UserCreate, UserUpdate
from app.services.init_admin import BUILTIN_ADMIN_EMAIL


router = APIRouter(
    prefix="/api/v1/users",
    tags=["users"],
)


# Solo ADMIN puede usar este router
def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return current_user


@router.get("/", response_model=List[UserRead], dependencies=[Depends(require_admin)])

def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    users = db.query(User).all()
    return users


@router.get("/{user_id}", response_model=UserRead, dependencies=[Depends(require_admin)])

def get_user(
    user_id: int,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])

def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
):
    # verificar email único
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=UserRole.MEMBER,   # se puede ajustar luego vía update
        is_active=payload.is_active,
        is_blocked=payload.is_blocked,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.put("/{user_id}", response_model=UserRead, dependencies=[Depends(require_admin)])

def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # no permitir cambiar al built-in admin a inactivo/bloqueado si quieres protegerlo más
    update_data = payload.model_dump(exclude_unset=True)
    new_password = update_data.pop("new_password", None)

    for field, value in update_data.items():
        setattr(user, field, value)

    if new_password:
        user.hashed_password = hash_password(new_password)

    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])

def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # proteger admin embebido
    if user.email == "admin@library.local":
        raise HTTPException(status_code=400, detail="Built-in admin cannot be deleted")

    db.delete(user)
    db.commit()
    return None

