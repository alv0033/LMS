from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError

from app.api.v1.dependencies import get_db
from app.core.security import decode_access_token
from app.db.models import User, UserRole


# Esta URL debe coincidir con tu endpoint de login
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Obtiene el usuario actual a partir del token JWT.
    Lanza 401 si no se puede validar.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )

    try:
        payload = decode_access_token(token)
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception

        # En el modelo User, id es Integer, no UUID
        user_id = int(user_id_str)
        
    except (JWTError, ValueError):
        raise credentials_exception

    user: User | None = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        raise credentials_exception

    return user


def require_role(required_role: UserRole):
    """
    Dependencia para exigir un rol mínimo.
    Admin siempre tiene acceso.
    """
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role != required_role and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return dependency
