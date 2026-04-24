from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from core.database import get_db
from core.security import get_current_user
from services.informe_service import InformeService
from schemas.all_schemas import InformesStats

router = APIRouter(prefix="/api/informes", tags=["Informes"])


def get_service(db: Session = Depends(get_db)) -> InformeService:
    return InformeService(db)


@router.get("/", response_model=InformesStats)
def get_informes(
    periodo: str = Query("30d", description="hoy | ayer | 7d | 30d | personalizado"),
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None,
    service: InformeService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    return service.stats(current_user.id, periodo, fecha_inicio, fecha_fin)
