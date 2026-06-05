"""
services/plan_service.py
────────────────────────
Gestión del plan y suscripción de cada negocio.

Estados del plan:
  'trial'      → 30 días de prueba con todo incluido desde el registro
  'activo'     → Plan pago vigente ($250.000 COP/mes)
  'suspendido' → Trial vencido o pago fallido — acceso limitado

Acceso por estado:
  trial activo  → todas las funcionalidades
  activo        → todas las funcionalidades
  trial vencido → solo lectura de citas existentes
  suspendido    → solo lectura de citas existentes
"""

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from models.all_models import Negocio


def get_estado_plan(negocio: Negocio) -> dict:
    """
    Calcula el estado actual del plan de un negocio.

    Returns:
        dict con:
          - plan: 'trial' | 'activo' | 'suspendido'
          - activo: True si tiene acceso completo
          - dias_restantes: int (solo en trial)
          - vencido: True si el trial expiró
          - mensaje: texto para mostrar al usuario
          - plan_expira_en: datetime de expiración
    """
    plan = negocio.plan or "trial"
    expira = negocio.plan_expira_en

    # Plan de pago activo → acceso total sin restricciones
    if plan == "activo":
        return {
            "plan": "activo",
            "activo": True,
            "dias_restantes": None,
            "vencido": False,
            "mensaje": "Plan activo",
            "plan_expira_en": expira,
        }

    # Plan trial → verificar si aún está vigente
    if plan == "trial":
        if expira is None:
            # Negocio existente sin fecha — darle acceso por defecto
            return {
                "plan": "trial",
                "activo": True,
                "dias_restantes": 30,
                "vencido": False,
                "mensaje": "Período de prueba",
                "plan_expira_en": None,
            }

        ahora = datetime.now(timezone.utc)
        # Normalizar timezone
        if expira.tzinfo is None:
            from datetime import timezone as tz
            expira = expira.replace(tzinfo=tz.utc)

        dias = (expira - ahora).days

        if dias >= 0:
            return {
                "plan": "trial",
                "activo": True,
                "dias_restantes": dias + 1,
                "vencido": False,
                "mensaje": f"Prueba gratuita — {dias + 1} día{'s' if dias > 0 else ''} restante{'s' if dias > 0 else ''}",
                "plan_expira_en": expira,
            }
        else:
            return {
                "plan": "trial",
                "activo": False,
                "dias_restantes": 0,
                "vencido": True,
                "mensaje": "Tu período de prueba ha vencido. Activa tu plan para continuar.",
                "plan_expira_en": expira,
            }

    # Plan suspendido
    return {
        "plan": "suspendido",
        "activo": False,
        "dias_restantes": 0,
        "vencido": True,
        "mensaje": "Plan suspendido. Contacta con soporte.",
        "plan_expira_en": expira,
    }


def activar_plan(negocio: Negocio, db: Session) -> Negocio:
    """
    Activa el plan de pago de un negocio (se llama desde el webhook de Wompi).
    El plan 'activo' no tiene fecha de expiración — se renueva con cada pago.
    """
    from datetime import timedelta
    negocio.plan = "activo"
    negocio.plan_expira_en = datetime.now(timezone.utc) + timedelta(days=32)  # margen
    negocio.ultimo_pago = datetime.now(timezone.utc)
    db.commit()
    return negocio


def suspender_plan(negocio: Negocio, db: Session) -> Negocio:
    """Suspende el plan de un negocio por falta de pago."""
    negocio.plan = "suspendido"
    db.commit()
    return negocio
