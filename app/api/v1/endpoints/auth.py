from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

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
            status_code=status.HTTP_400_BAD_REQUEST,
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
            "Login failed",
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
        "Login succeeded",
        extra={
            "operation": "auth_login",
            "resource": "user",
            "email": email,
            "status_code": 200,
            "ip": client_ip,
        },
    )

    return Token(access_token=access_token)