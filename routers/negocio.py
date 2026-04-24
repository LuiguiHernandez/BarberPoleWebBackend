from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
from core.database import get_db
from core.security import get_current_user
from services.negocio_service import NegocioService
from schemas.all_schemas import NegocioUpdate, NegocioResponse

router = APIRouter(prefix="/api/negocio", tags=["Negocio"])


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
