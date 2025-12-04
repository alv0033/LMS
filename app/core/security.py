from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.db.models import UserRole

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    user_id: int,
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    expire = datetime.now(timezone.utc) + expires_delta

    to_encode = {
        "sub": str(user_id),
        "role": role,
        "exp": expire,
    }

    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
         #Decodifica el JWT y normaliza user_id como int.

           # Devuelve:
            # dict con al menos: user_id (int), role (str)
            # None si el token es inválido o expirado
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])

        sub = payload.get("sub")
        if sub is None:
            return None

        # convertir a int
        try:
            user_id = int(sub)
        except (TypeError, ValueError):
            return None

        normalized = dict(payload)
        normalized["user_id"] = user_id
        return normalized

    except JWTError:
        return None
