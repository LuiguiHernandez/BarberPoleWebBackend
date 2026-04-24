from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException
from models.all_models import Cliente
from repositories.cliente_repository import ClienteRepository
from repositories.negocio_repository import NegocioRepository
from schemas.all_schemas import LealtadResumen, ClienteResponse


class LealtadService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ClienteRepository(db)
        self.negocio_repo = NegocioRepository(db)

    def _get_negocio(self, usuario_id: int):
        negocio = self.negocio_repo.get_by_usuario_id(usuario_id)
        if not negocio:
            raise HTTPException(status_code=404, detail="Negocio no encontrado")
        return negocio

    def clientes(self, usuario_id: int, q: Optional[str]) -> List[Cliente]:
        negocio = self._get_negocio(usuario_id)
        return self.repo.get_by_negocio(negocio.id, q)

    def dar_sello(self, usuario_id: int, telefono: str) -> dict:
        negocio = self._get_negocio(usuario_id)
        cliente = self.repo.get_by_telefono(negocio.id, telefono)
        if not cliente:
            raise HTTPException(
                status_code=404, detail="Cliente no encontrado con ese teléfono"
            )

        cliente.sellos += 1
        cliente.sellos_totales += 1

        recompensa_ganada = False
        if cliente.sellos >= negocio.lealtad_sellos_requeridos:
            cliente.sellos = 0
            cliente.recompensas_canjeadas += 1
            recompensa_ganada = True

        self.db.commit()
        return {
            "cliente": cliente.nombre,
            "sellos_actuales": cliente.sellos,
            "recompensa_ganada": recompensa_ganada,
            "recompensa": negocio.lealtad_recompensa if recompensa_ganada else None,
        }

    def resumen(self, usuario_id: int) -> LealtadResumen:
        negocio = self._get_negocio(usuario_id)
        return LealtadResumen(
            total_clientes=self.repo.count_by_negocio(negocio.id),
            sellos_dados_hoy=0,
            recompensas_canjeadas_total=self.repo.sum_recompensas(negocio.id),
        )
