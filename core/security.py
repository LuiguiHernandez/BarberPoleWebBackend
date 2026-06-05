"""
core/security.py
────────────────
Autenticación y autorización de GestorPro.

Responsabilidades:
- Crear y validar tokens JWT (access 15min + refresh 7 días)
- Hashing y verificación de contraseñas con bcrypt
- Dependencias FastAPI para proteger endpoints
- Rate limiting integrado (slowapi)

Uso en routers:
    @router.get("/mis-citas")
    def ver_citas(current_user = Depends(get_current_user)):
        # current_user es el objeto Usuario de la BD
        ...

    @router.post("/admin/negocio")
    def crear_negocio(current_user = Depends(require_superadmin)):
        # Solo accesible si current_user.rol == 'superadmin'
        ...
"""

from datetime import datetime, timedelta
from typing import Optional
import bcrypt as _bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from core.config import settings
from core.database import get_db

bearer_scheme = HTTPBearer()

# ── Duración de tokens ─────────────────────────────────────────────────────────
# access_token corto (15min): minimiza el daño si se roba
# refresh_token largo (7 días): permite renovar sin pedir contraseña de nuevo
ACCESS_TOKEN_EXPIRE  = timedelta(minutes=15)
REFRESH_TOKEN_EXPIRE = timedelta(days=7)


def hash_password(password: str) -> str:
    """Genera un hash bcrypt de la contraseña. Incluye salt automático."""
    return _bcrypt.hashpw(password.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verifica si una contraseña en texto plano coincide con su hash bcrypt."""
    return _bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Crea un JWT de corta duración para autenticar peticiones.

    Args:
        data: Payload del token. Debe incluir {"sub": str(user_id)}.
        expires_delta: Duración personalizada. Por defecto ACCESS_TOKEN_EXPIRE (15min).

    Returns:
        Token JWT firmado como string.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or ACCESS_TOKEN_EXPIRE)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """
    Crea un JWT de larga duración para renovar el access_token.

    El refresh_token se usa en POST /api/auth/refresh.
    Incluye el campo "type": "refresh" para distinguirlo del access_token.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + REFRESH_TOKEN_EXPIRE
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decodifica y valida un token JWT.

    Raises:
        HTTPException 401: si el token es inválido, expirado o mal firmado.

    Returns:
        El payload del token como dict.
    """
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    """
    Dependencia FastAPI para endpoints protegidos.

    Valida el Bearer token del header Authorization,
    busca el usuario en la BD y lo retorna.

    Uso:
        @router.get("/citas")
        def listar(user = Depends(get_current_user)):
            ...

    Raises:
        HTTPException 401: token inválido o usuario no encontrado.
        HTTPException 403: usuario suspendido (activo=False).
    """
    payload = decode_token(credentials.credentials)
    user_id: int = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Token inválido")

    from models.all_models import Usuario
    user = db.query(Usuario).filter(Usuario.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    if hasattr(user, 'activo') and user.activo is False:
        raise HTTPException(status_code=403, detail="Cuenta suspendida")
    return user


def require_superadmin(current_user=Depends(get_current_user)):
    """
    Dependencia FastAPI para endpoints exclusivos de superadmin.

    Uso:
        @router.post("/admin/negocios")
        def crear(admin = Depends(require_superadmin)):
            ...

    Raises:
        HTTPException 403: si el usuario no tiene rol 'superadmin'.
    """
    if not hasattr(current_user, 'rol') or current_user.rol != "superadmin":
        raise HTTPException(
            status_code=403,
            detail="Acceso denegado — se requiere rol de administrador"
        )
    return current_user


def require_cliente(current_user=Depends(get_current_user)):
    """
    Dependencia para endpoints accesibles por cualquier usuario autenticado.
    Alias semántico de get_current_user, permite cliente y superadmin.
    """
    return current_user
