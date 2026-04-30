from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException
from models.all_models import Conversacion, Mensaje, Cliente
from repositories.conversacion_repository import ConversacionRepository, MensajeRepository
from repositories.negocio_repository import NegocioRepository
from repositories.cliente_repository import ClienteRepository
from services.whatsapp_service import WhatsAppService


class ConversacionService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ConversacionRepository(db)
        self.msg_repo = MensajeRepository(db)
        self.negocio_repo = NegocioRepository(db)
        self.cliente_repo = ClienteRepository(db)
        self.whatsapp = WhatsAppService()

    def _negocio_id(self, usuario_id: int) -> int:
        negocio = self.negocio_repo.get_by_usuario_id(usuario_id)
        if not negocio:
            raise HTTPException(status_code=404, detail="Negocio no encontrado")
        return negocio.id

    def listar(self, usuario_id: int, q: Optional[str]) -> List[Conversacion]:
        return self.repo.get_by_negocio(self._negocio_id(usuario_id), q)

    def mensajes(self, usuario_id: int, conv_id: int) -> List[Mensaje]:
        negocio_id = self._negocio_id(usuario_id)
        conv = self.repo.get_by_id_and_negocio(conv_id, negocio_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversación no encontrada")
        self.msg_repo.marcar_leidos(conv_id)
        conv.no_leidos = 0
        self.db.commit()
        return self.msg_repo.get_by_conversacion(conv_id)

    async def responder(self, usuario_id: int, conv_id: int, contenido: str) -> dict:
        negocio_id = self._negocio_id(usuario_id)
        conv = self.repo.get_by_id_and_negocio(conv_id, negocio_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversación no encontrada")

        try:
            await self.whatsapp.enviar_mensaje(conv.telefono, contenido)
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Error enviando WhatsApp: {str(e)}")

        mensaje = Mensaje(
            conversacion_id=conv_id,
            contenido=contenido,
            enviado_por="barberia",
        )
        self.db.add(mensaje)
        conv.ultimo_mensaje = contenido
        conv.ultimo_mensaje_en = datetime.utcnow()
        self.db.commit()
        return {"ok": True}

    def procesar_webhook(
        self,
        negocio_slug: str,
        telefono: str,
        nombre: Optional[str],
        mensaje_texto: str,
        enviado_por_mi: bool = False,
    ) -> dict:
        negocio = self.negocio_repo.get_by_slug(negocio_slug)
        if not negocio:
            raise HTTPException(status_code=404, detail="Negocio no encontrado")

        # Limpiar el teléfono para evitar duplicados por formato
        telefono = telefono.strip()

        conv = self.repo.get_by_telefono(negocio.id, telefono)
        
        if not conv:
            # Lógica de creación de cliente y conversación (se mantiene igual)
            cliente = self.cliente_repo.get_by_telefono(negocio.id, telefono)
            if not cliente and nombre:
                cliente = Cliente(negocio_id=negocio.id, nombre=nombre, telefono=telefono)
                self.db.add(cliente)
                self.db.flush()

            conv = Conversacion(
                negocio_id=negocio.id,
                cliente_id=cliente.id if cliente else None,
                telefono=telefono,
                nombre_contacto=nombre or telefono,
            )
            self.db.add(conv)
            self.db.flush()

        # DETERMINAR EL REMITENTE
        # Si 'enviado_por_mi' es True, el mensaje viene del barbero (desde el celular)
        remitente = "barberia" if enviado_por_mi else "cliente"

        mensaje = Mensaje(
            conversacion_id=conv.id,
            contenido=mensaje_texto,
            enviado_por=remitente, # <--- Dinámico
        )
        self.db.add(mensaje)
        
        # ACTUALIZAR EL SNIPPET DE LA BARRA LATERAL
        conv.ultimo_mensaje = mensaje_texto
        conv.ultimo_mensaje_en = datetime.utcnow()
        
        # Solo aumentar no leídos si es un mensaje del cliente
        if not enviado_por_mi:
            conv.no_leidos += 1
            
        self.db.commit()
        return {"ok": True, "conversacion_id": conv.id, "negocio": negocio}

    def guardar_respuesta_Carlos(
        self, conversacion_id: int, respuesta: str, telefono: Optional[str]
    ) -> Conversacion:
        conv = self.repo.get_by_id(conversacion_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversación no encontrada")

        mensaje = Mensaje(
            conversacion_id=conversacion_id,
            contenido=respuesta,
            enviado_por="Carlos",
        )
        self.db.add(mensaje)
        conv.ultimo_mensaje = respuesta
        conv.ultimo_mensaje_en = datetime.utcnow()
        self.db.commit()
        return conv
