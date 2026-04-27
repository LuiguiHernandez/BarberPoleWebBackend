from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from core.security import get_current_user
from services.auth_service import AuthService
from schemas.all_schemas import LoginRequest, TokenResponse, RegisterRequest

router = APIRouter()


def get_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)


@router.post("/register", response_model=TokenResponse)
def register(data: RegisterRequest, service: AuthService = Depends(get_service)):
    return service.register(data)


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, service: AuthService = Depends(get_service)):
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
