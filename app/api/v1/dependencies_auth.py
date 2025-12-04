from fastapi import Depends, HTTPException, status,  Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
#from jose import JWTError

from app.api.v1.dependencies import get_db
from app.core.security import decode_access_token
from app.db.models import User, UserRole
from app.core.logging import user_id_ctx


# Esta URL debe coincidir con tu endpoint de login
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Obtiene el usuario actual a partir del token JWT.
    Lanza 401 si no se puede validar.
    """

     # 1) Revisar si el token ha sido revocado
    revoked_tokens = getattr(request.app.state, "revoked_tokens", set())
    if token in revoked_tokens:
        raise HTTPException(
            status_code=401,
            detail="Token revoked",
        )

        
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
    )

   # Decodificar el token (lanza excepción si es inválido)
    payload = decode_access_token(token)
    
    if payload is None:
        raise credentials_exception

    user_id: int = payload.get("user_id") or payload.get("sub")
    if user_id is None:
        raise credentials_exception

    # convertir a int para que la consulta funcione
    try:
        user_id = int(user_id)
    except:
        raise credentials_exception
    

    # Obtener usuario de la BD
    user: User | None = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    
    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        raise credentials_exception

    # Validar estado del usuario
    if not user.is_active or user.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive or blocked",
        )

    # Guardar user_id para LOGGING estructurado
    user_id_ctx.set(str(user.id))

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
