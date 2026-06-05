from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session
from core.database import get_db
from core.security import get_current_user
from services.auth_service import AuthService
from schemas.all_schemas import LoginRequest, TokenResponse, RegisterRequest

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


def get_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)


@router.post("/register", response_model=TokenResponse)
@limiter.limit("10/minute")
def register(request: Request, data: RegisterRequest, service: AuthService = Depends(get_service)):
    return service.register(data)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(request: Request, data: LoginRequest, service: AuthService = Depends(get_service)):
    return service.login(data)


@router.get("/me")
def me(current_user=Depends(get_current_user)):
    negocio = current_user.negocio
    return {
        "id": current_user.id,
        "nombre": current_user.nombre,
        "email": current_user.email,
        "negocio": {
            "id": negocio.id,
            "nombre": negocio.nombre,
            "slug": negocio.slug,
        } if negocio else None,
    }


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(data: RefreshRequest, service: AuthService = Depends(get_service)):
    """Genera un nuevo access_token usando el refresh_token."""
    return service.refresh(data.refresh_token)
