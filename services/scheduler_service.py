"""
services/scheduler_service.py
─────────────────────────────
Tareas programadas que corren en background desde el inicio de la app.

El scheduler se inicia en main.py usando el mecanismo lifespan de FastAPI:

    @asynccontextmanager
    async def lifespan(app):
        task = asyncio.create_task(loop_scheduler())
        yield
        task.cancel()

Tareas activas:
  - job_recordatorios(): corre cada 15 minutos.
    Busca citas que empiecen en ~2 horas y envía WhatsApp de recordatorio.
    Ventana de búsqueda: ±15 minutos alrededor de "ahora + 2h".

  - job_resumen_diario(): corre una vez al día a las 7:30am hora Colombia.
    Envía al número del negocio la lista de citas del día con total estimado.

Horario de Colombia: ZoneInfo("America/Bogota") — UTC-5
SchedulerService — Tareas programadas
- Recordatorios WhatsApp 2h antes de cada cita
- Resumen diario al dueño del negocio a las 7:30am
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

COL_TZ = ZoneInfo("America/Bogota")


async def job_recordatorios():
    """
    Corre cada 15 minutos.
    Busca citas que empiecen en ~2h y envía recordatorio si no se envió aún.
    """
    from core.database import SessionLocal
    from models.all_models import Cita, Negocio, EstadoCita
    from services.whatsapp_service import WhatsAppService

    db = SessionLocal()
    wa = WhatsAppService()
    try:
        ahora    = datetime.now(COL_TZ)
        en_2h    = ahora + timedelta(hours=2)
        ventana  = timedelta(minutes=15)  # ±15min

        citas = db.query(Cita).filter(
            Cita.fecha_hora >= en_2h - ventana,
            Cita.fecha_hora <= en_2h + ventana,
            Cita.estado.in_([EstadoCita.pendiente, EstadoCita.confirmada]),
        ).all()

        if citas:
            logger.info(f"[SCHEDULER] Recordatorios: {len(citas)} citas en ~2h")

        for cita in citas:
            try:
                cliente = cita.cliente
                if not cliente or not cliente.telefono:
                    continue
                negocio = db.query(Negocio).filter(Negocio.id == cita.negocio_id).first()
                servicio_nombre = cita.servicio.nombre if cita.servicio else "Cita"
                profesional     = cita.barbero.nombre  if cita.barbero  else ""
                hora_str = cita.fecha_hora.astimezone(COL_TZ).strftime("%-I:%M %p").replace("AM","a.m.").replace("PM","p.m.")

                ok = await wa.recordatorio_2h(
                    telefono       = cliente.telefono,
                    nombre_cliente = cliente.nombre or "Cliente",
                    nombre_negocio = negocio.nombre if negocio else "el negocio",
                    servicio       = servicio_nombre,
                    hora           = hora_str,
                    profesional    = profesional,
                    direccion      = negocio.direccion if negocio else "",
                )
                if ok:
                    logger.info(f"[SCHEDULER] Recordatorio enviado → cita {cita.id} cliente {cliente.nombre}")
            except Exception as e:
                logger.error(f"[SCHEDULER] Error recordatorio cita {cita.id}: {e}")
    finally:
        db.close()


async def job_resumen_diario():
    """
    Corre cada día a las 7:30am hora Colombia.
    Envía a cada negocio su resumen de citas del día.
    """
    from core.database import SessionLocal
    from models.all_models import Cita, Negocio, Usuario, EstadoCita
    from services.whatsapp_service import WhatsAppService
    from sqlalchemy import func

    db = SessionLocal()
    wa = WhatsAppService()
    try:
        ahora  = datetime.now(COL_TZ)
        inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
        fin    = ahora.replace(hour=23, minute=59, second=59)

        negocios = db.query(Negocio).all()
        fecha_str = ahora.strftime("%-d de %B de %Y")

        for negocio in negocios:
            try:
                # Teléfono del dueño del negocio
                usuario = db.query(Usuario).filter(Usuario.id == negocio.usuario_id).first()
                telefono_dueno = negocio.telefono or (usuario.telefono if hasattr(usuario, 'telefono') and usuario else None)
                if not telefono_dueno:
                    continue

                citas_hoy = db.query(Cita).filter(
                    Cita.negocio_id == negocio.id,
                    Cita.fecha_hora >= inicio,
                    Cita.fecha_hora <= fin,
                    Cita.estado.in_([EstadoCita.pendiente, EstadoCita.confirmada, EstadoCita.completada]),
                ).order_by(Cita.fecha_hora).all()

                citas_data = []
                total = 0.0
                for c in citas_hoy:
                    hora_cita = c.fecha_hora.astimezone(COL_TZ).strftime("%-I:%M %p").replace("AM","a.m.").replace("PM","p.m.")
                    citas_data.append({
                        "hora":        hora_cita,
                        "nombre":      c.cliente.nombre if c.cliente else "Cliente",
                        "servicio":    c.servicio.nombre if c.servicio else "Servicio",
                        "profesional": c.barbero.nombre  if c.barbero  else "",
                    })
                    total += c.precio or 0

                await wa.resumen_diario(
                    telefono_dueno = telefono_dueno,
                    nombre_negocio = negocio.nombre,
                    fecha_str      = fecha_str,
                    citas          = citas_data,
                    total_estimado = total,
                )
                logger.info(f"[SCHEDULER] Resumen enviado → {negocio.nombre} ({len(citas_data)} citas)")
            except Exception as e:
                logger.error(f"[SCHEDULER] Error resumen {negocio.nombre}: {e}")
    finally:
        db.close()


async def loop_scheduler():
    """Loop principal del scheduler. Corre en background desde FastAPI."""
    import asyncio

    logger.info("[SCHEDULER] Iniciado ✓")
    ultimo_resumen_dia = None

    while True:
        try:
            ahora = datetime.now(COL_TZ)

            # Recordatorios: cada 15 minutos
            await job_recordatorios()

            # Resumen diario: una vez al día a las 7:30am
            hoy = ahora.date()
            if (ahora.hour == 7 and ahora.minute >= 30 and ultimo_resumen_dia != hoy):
                await job_resumen_diario()
                ultimo_resumen_dia = hoy

        except Exception as e:
            logger.error(f"[SCHEDULER] Error en loop: {e}")

        # Esperar 15 minutos
        await asyncio.sleep(15 * 60)
