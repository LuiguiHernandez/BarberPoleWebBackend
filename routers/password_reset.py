"""
Endpoints de recuperación de contraseña y verificación de email.
"""
import uuid
import asyncio
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from core.database import get_db
from core.security import hash_password

router = APIRouter(prefix="/api/auth", tags=["auth"])

# ── Schemas ───────────────────────────────────────────────────────────────────
class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    nueva_password: str

class VerifyEmailRequest(BaseModel):
    token: str

# ── Almacenamiento en memoria (simple, funciona para MVP) ─────────────────────
# En producción escalar a BD o Redis
_reset_tokens:  dict[str, dict] = {}   # token → {user_id, expires}
_verify_tokens: dict[str, dict] = {}   # token → {user_id, expires}


@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Genera un token de recuperación y envía email.
    Siempre responde igual para no revelar si el email existe.
    """
    from models.all_models import Usuario
    usuario = db.query(Usuario).filter(Usuario.email == data.email).first()

    if usuario:
        # Generar token único
        token = str(uuid.uuid4())
        _reset_tokens[token] = {
            "user_id": usuario.id,
            "expires": datetime.utcnow() + timedelta(hours=1),
        }

        # URL del frontend
        from core.config import settings
        frontend = settings.FRONTEND_URL.rstrip("/")
        link = f"{frontend}/reset-password?token={token}"

        # Enviar email de forma async (no bloquear la respuesta)
        from services.email_service import send_email, html_recuperar_password
        asyncio.create_task(send_email(
            to=usuario.email,
            subject="Recuperar contraseña — GestorPro",
            html=html_recuperar_password(usuario.nombre or "Usuario", link),
        ))

    return {"ok": True, "mensaje": "Si el email existe, recibirás un enlace en los próximos minutos."}


@router.post("/reset-password")
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Valida el token y actualiza la contraseña."""
    entry = _reset_tokens.get(data.token)
    if not entry:
        raise HTTPException(status_code=400, detail="Token inválido o ya utilizado")
    if datetime.utcnow() > entry["expires"]:
        del _reset_tokens[data.token]
        raise HTTPException(status_code=400, detail="El enlace expiró. Solicita uno nuevo.")
    if len(data.nueva_password) < 6:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres")

    from models.all_models import Usuario
    usuario = db.query(Usuario).filter(Usuario.id == entry["user_id"]).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    usuario.password_hash = hash_password(data.nueva_password)
    db.commit()

    # Invalidar el token
    del _reset_tokens[data.token]

    return {"ok": True, "mensaje": "Contraseña actualizada correctamente. Ya puedes iniciar sesión."}


@router.post("/verify-email")
def verify_email(data: VerifyEmailRequest, db: Session = Depends(get_db)):
    """Verifica el email del usuario."""
    entry = _verify_tokens.get(data.token)
    if not entry:
        raise HTTPException(status_code=400, detail="Token inválido")
    if datetime.utcnow() > entry["expires"]:
        del _verify_tokens[data.token]
        raise HTTPException(status_code=400, detail="El enlace de verificación expiró")

    from models.all_models import Usuario
    usuario = db.query(Usuario).filter(Usuario.id == entry["user_id"]).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Marcar email como verificado (columna email_verificado)
    if hasattr(usuario, 'email_verificado'):
        usuario.email_verificado = True
        db.commit()

    del _verify_tokens[data.token]
    return {"ok": True, "mensaje": "Email verificado correctamente."}


def crear_token_verificacion(user_id: int) -> str:
    """Crea un token de verificación de email para un usuario recién registrado."""
    token = str(uuid.uuid4())
    _verify_tokens[token] = {
        "user_id": user_id,
        "expires": datetime.utcnow() + timedelta(hours=24),
    }
    return token
