"""
Router Kommo — endpoints para conectar y gestionar la integración con Kommo CRM
"""
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from core.database import get_db
from core.security import get_current_user
from services.kommo_service import KommoService

router = APIRouter()


def get_service(db: Session = Depends(get_db)) -> KommoService:
    return KommoService(db)


# ── Estado de conexión ────────────────────────────────────────────
@router.get("/estado")
def estado(
    service: KommoService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    """Devuelve si Kommo está conectado y datos básicos de la cuenta."""
    return service.estado(current_user.id)


# ── Conectar con token manual ─────────────────────────────────────
class KommoConectarRequest(BaseModel):
    access_token: str
    base_url: str     # https://tusubdominio.kommo.com


@router.post("/conectar")
def conectar(
    data: KommoConectarRequest,
    service: KommoService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    """
    Conecta Kommo con un Long-Lived Token.
    El usuario lo obtiene en: Kommo → Ajustes → Integraciones → API → Clave API larga duración
    """
    return service.conectar_manual(current_user.id, data.access_token, data.base_url)


@router.post("/desconectar")
def desconectar(
    service: KommoService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    return service.desconectar(current_user.id)


# ── Webhook entrante de Kommo ─────────────────────────────────────
@router.post("/webhook/{slug}")
async def webhook_entrante(
    slug: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Kommo envía aquí los mensajes entrantes de WhatsApp.
    URL a configurar en Kommo: https://tudominio.com/api/kommo/webhook/{slug}
    """
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    service = KommoService(db)
    return service.procesar_webhook(slug, payload)


# ── Enviar mensaje desde GestorPro ───────────────────────────────
class EnviarRequest(BaseModel):
    conversacion_id: int
    texto: str


@router.post("/enviar")
async def enviar_mensaje(
    data: EnviarRequest,
    service: KommoService = Depends(get_service),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Envía un mensaje desde el panel de Conversaciones de GestorPro vía Kommo."""
    from models.all_models import Conversacion, Mensaje
    from repositories.negocio_repository import NegocioRepository
    from datetime import datetime

    negocio = NegocioRepository(db).get_by_usuario_id(current_user.id)
    if not negocio:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    conv = db.query(Conversacion).filter(
        Conversacion.id == data.conversacion_id,
        Conversacion.negocio_id == negocio.id
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")

    # Enviar vía Kommo
    await service.enviar_por_negocio_id(negocio.id, conv.telefono, data.texto)

    # Guardar en BD
    msg = Mensaje(
        conversacion_id=conv.id,
        contenido=data.texto,
        enviado_por="barberia",
    )
    db.add(msg)
    conv.ultimo_mensaje    = data.texto
    conv.ultimo_mensaje_en = datetime.utcnow()
    db.commit()

    return {"ok": True}


# ── Sincronizar leads de Kommo → GestorPro ────────────────────────
@router.post("/sincronizar")
async def sincronizar_kommo(
    service: KommoService = Depends(get_service),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sincroniza contactos/leads de Kommo como clientes en GestorPro."""
    from repositories.negocio_repository import NegocioRepository
    negocio = NegocioRepository(db).get_by_usuario_id(current_user.id)
    if not negocio:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")
    return await service.sincronizar_citas_desde_kommo(negocio.id)


# ── Stats de Kommo para Informes ──────────────────────────────────
@router.get("/stats")
async def stats_kommo(
    service: KommoService = Depends(get_service),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Devuelve métricas de Kommo para mostrar en el panel de Informes."""
    from repositories.negocio_repository import NegocioRepository
    negocio = NegocioRepository(db).get_by_usuario_id(current_user.id)
    if not negocio:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")
    return await service.obtener_stats_kommo(negocio.id)
