import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.routing import APIRoute

from core.config import settings
from core.database import engine, Base

# Importación de modelos para creación de tablas
from models import Usuario, Negocio, Servicio, Barbero, Horario, Cliente, Cita, Conversacion, Mensaje, CarlosIndicacion

# Routers
from routers.auth import router as auth_router
from routers.citas import router as citas_router
from routers.negocio import router as negocio_router
from routers.servicios import router as servicios_router
from routers.barberos import router as barberos_router          # legado
from routers.profesionales import router as profesionales_router  # nuevo
from routers.horarios import router as horarios_router
from routers.informes import router as informes_router
from routers.lealtad import router as lealtad_router
from routers.conversaciones import router as conversaciones_router
from routers.carlos import router as carlos_router
from routers.webhooks import router as webhook_router
from routers.categorias import router as categorias_router
from routers.gcal import router as gcal_router
from routers.kommo import router as kommo_router
from routers.admin import router as admin_router
from routers.public_booking import router as public_router

# Crear tablas en Postgres
Base.metadata.create_all(bind=engine)

# Scheduler en background
@asynccontextmanager
async def lifespan(app: FastAPI):
    from services.scheduler_service import loop_scheduler
    task = asyncio.create_task(loop_scheduler())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

def custom_generate_unique_id(route: APIRoute):
    return f"{route.name}"

app = FastAPI(
    title="GestorPro API",
    generate_unique_id_function=custom_generate_unique_id,
    description="Backend para gestión de negocios de servicios",
    version="2.0.0",
    lifespan=lifespan,
)

# --- CONFIGURACIÓN DE CORS (UNIFICADA) ---
origins = [
    "http://167.172.145.102",
    "http://167.172.145.102:80",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://localhost:3000",
    "https://sensciencespa.com",
    "https://www.sensciencespa.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # público — el widget se embebe en cualquier dominio
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Configuración de archivos estáticos
os.makedirs("uploads", exist_ok=True)
os.makedirs("static", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- INCLUSIÓN DE ROUTERS CON PREFIJO /API ---
# Aseguramos que todos coincidan con las llamadas de Axios en el Front
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
app.include_router(citas_router, prefix="/api/citas", tags=["Citas"])
app.include_router(negocio_router, prefix="/api/negocio", tags=["Negocio"])
app.include_router(servicios_router, prefix="/api/servicios", tags=["Servicios"])
app.include_router(barberos_router,      prefix="/api/barberos",      tags=["Profesionales (legado)"])
app.include_router(profesionales_router, prefix="/api/profesionales", tags=["Profesionales"])
app.include_router(horarios_router, prefix="/api/horarios", tags=["Horarios"])
app.include_router(informes_router, prefix="/api/informes", tags=["Informes"])
app.include_router(lealtad_router, prefix="/api/lealtad", tags=["Lealtad"])
app.include_router(conversaciones_router, prefix="/api/conversaciones", tags=["Conversaciones"])
app.include_router(carlos_router, prefix="/api/carlos", tags=["Carlos"])
app.include_router(webhook_router, prefix="/api/webhooks", tags=["Webhooks"])
app.include_router(categorias_router, prefix="/api/categorias", tags=["Categorías"])
app.include_router(gcal_router,   prefix="/api/gcal",   tags=["Google Calendar"])
app.include_router(kommo_router,  prefix="/api/kommo",  tags=["Kommo CRM"])
app.include_router(admin_router,  prefix="/api/admin",  tags=["Admin"])
app.include_router(public_router, prefix="/api/public", tags=["Booking Público"])

@app.get("/", tags=["Health"])
def root():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": "2.0.0",
        "docs": "/docs",
    }

@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}