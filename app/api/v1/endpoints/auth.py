from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.api.v1.dependencies_auth import get_current_user
from app.api.v1.dependencies import get_db

from app.core.security import hash_password, verify_password, create_access_token
from app.db.models import User, UserRole
from app.schemas.user import UserCreate, UserRead
from app.schemas.auth import Token

import logging
logger = logging.getLogger("api.auth")

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["auth"],
)


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Email already registered",
        )

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=UserRole.MEMBER,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user



@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    request: Request = None,
):
    
    email = form_data.username
    password = form_data.password
    # username se usa como email
    user = db.query(User).filter(User.email == form_data.username).first()

    client_ip = request.client.host if request else None


    if not user or not verify_password(password, user.hashed_password):
        logger.warning(
            "login_failed",
            extra={
                "operation": "auth_login",
                "resource": "user",
                "email": email,
                "status_code": 401,
                "ip": client_ip,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    access_token = create_access_token(user_id=user.id, role=user.role.name)

    logger.info(
        "login_success",
        extra={
            "operation": "auth_login",
            "resource": "user",
            "email": email,
            "status_code": 200,
            "ip": client_ip,
        },
    )

    return Token(access_token=access_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    Logout: revoca el token actual del usuario.
    """

    # Extraer el token crudo del header Authorization
    auth_header = request.headers.get("Authorization", "")
    parts = auth_header.split()
    token = parts[1] if len(parts) == 2 and parts[0].lower() == "bearer" else None

    if token:
        # Inicializar el set de tokens revocados si no existe
        if not hasattr(request.app.state, "revoked_tokens"):
            request.app.state.revoked_tokens = set()

        request.app.state.revoked_tokens.add(token)

    logger.info(
        "Logout succeeded",
        extra={
            "operation": "auth_logout",
            "resource": "user",
            "email": current_user.email,
            "user_id": current_user.id,
            "status_code": 204,
            "ip": request.client.host if request and request.client else None,
        },
    )

    # 204 No Content (no devuelve body)
    return