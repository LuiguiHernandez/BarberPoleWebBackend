from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from fastapi.routing import APIRoute

from core.config import settings
from core.database import engine, Base


from models import Usuario, Negocio, Servicio, Barbero, Horario, Cliente, Cita, Conversacion, Mensaje, LunaIndicacion

from routers.auth import router as auth_router
from routers.citas import router as citas_router
from routers.negocio import router as negocio_router
from routers.servicios import router as servicios_router
from routers.barberos import router as barberos_router
from routers.horarios import router as horarios_router
from routers.informes import router as informes_router
from routers.lealtad import router as lealtad_router
from routers.conversaciones import router as conversaciones_router
from routers.luna import router as luna_router
from routers.webhooks import router as webhook_router

Base.metadata.create_all(bind=engine)

def custom_generate_unique_id(route: APIRoute):
    # Esto hace que el ID sea solo "login" o "register" en lugar de nombres largos
    return f"{route.name}"

app = FastAPI(
    title="BarberPole API",
    generate_unique_id_function=custom_generate_unique_id,
    description="Backend completo para gestión de barberías",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
app.include_router(citas_router)
app.include_router(negocio_router)
app.include_router(servicios_router)
app.include_router(barberos_router)
app.include_router(horarios_router)
app.include_router(informes_router)
app.include_router(lealtad_router)
app.include_router(conversaciones_router)
app.include_router(luna_router)
app.include_router(webhook_router)


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
