from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
from core.database import get_db
from core.security import get_current_user
from services.negocio_service import NegocioService
from schemas.all_schemas import NegocioUpdate, NegocioResponse

router = APIRouter()


def get_service(db: Session = Depends(get_db)) -> NegocioService:
    return NegocioService(db)


@router.get("/", response_model=NegocioResponse)
def get_negocio(
    service: NegocioService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    return service.get(current_user.id)


@router.put("/", response_model=NegocioResponse)
def update_negocio(
    data: NegocioUpdate,
    service: NegocioService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    return service.update(current_user.id, data)


@router.post("/logo")
async def upload_logo(
    file: UploadFile = File(...),
    service: NegocioService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    return await service.upload_logo(current_user.id, file)


# ── Temas y personalización visual ───────────────────────────────
from pydantic import BaseModel as PM
from typing import Optional as Opt

class TemaRequest(PM):
    tipo_negocio:      Opt[str] = None
    color_primario:    Opt[str] = None
    color_secundario:  Opt[str] = None
    color_fondo:       Opt[str] = None
    color_texto:       Opt[str] = None
    url_web:           Opt[str] = None

@router.get("/temas")
def listar_temas():
    """Devuelve todos los temas predefinidos disponibles."""
    from core.temas import TEMAS
    return [
        {"tipo": k, "label": v["label"], "emoji": v["emoji"],
         "color_primario": v["color_primario"], "color_fondo": v["color_fondo"]}
        for k, v in TEMAS.items()
    ]

@router.put("/tema")
def actualizar_tema(
    data: TemaRequest,
    service: NegocioService = Depends(get_service),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Actualiza el tema visual y URL web del negocio."""
    from models.all_models import Negocio
    from repositories.negocio_repository import NegocioRepository
    from core.temas import get_tema, get_tema_negocio

    negocio = NegocioRepository(db).get_by_usuario_id(current_user.id)
    if not negocio:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    # Si cambia el tipo, aplicar colores predefinidos como base
    if data.tipo_negocio and data.tipo_negocio != negocio.tipo_negocio:
        predefinido = get_tema(data.tipo_negocio)
        negocio.tipo_negocio     = data.tipo_negocio
        negocio.color_primario   = data.color_primario   or predefinido["color_primario"]
        negocio.color_secundario = data.color_secundario or predefinido["color_secundario"]
        negocio.color_fondo      = data.color_fondo      or predefinido["color_fondo"]
        negocio.color_texto      = data.color_texto      or predefinido["color_texto"]
    else:
        # Solo actualizar los colores que llegaron
        if data.color_primario:   negocio.color_primario   = data.color_primario
        if data.color_secundario: negocio.color_secundario = data.color_secundario
        if data.color_fondo:      negocio.color_fondo      = data.color_fondo
        if data.color_texto:      negocio.color_texto      = data.color_texto

    if data.url_web is not None:
        negocio.url_web = data.url_web or None

    db.commit()
    db.refresh(negocio)
    return {"ok": True, "tema": get_tema_negocio(negocio)}

@router.get("/tema")
def get_tema_actual(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Devuelve el tema actual del negocio autenticado."""
    from models.all_models import Negocio
    from repositories.negocio_repository import NegocioRepository
    from core.temas import get_tema_negocio, TEMAS

    negocio = NegocioRepository(db).get_by_usuario_id(current_user.id)
    if not negocio:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Negocio no encontrado")
    return {
        "tema_actual": get_tema_negocio(negocio),
        "url_web": negocio.url_web,
        "temas_disponibles": [
            {"tipo": k, "label": v["label"], "emoji": v["emoji"],
             "color_primario": v["color_primario"], "color_fondo": v["color_fondo"]}
            for k, v in TEMAS.items()
        ]
    }
