from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from core.config import settings
from core.database import engine, Base

import models.all_models  # noqa — registra todos los modelos en SQLAlchemy

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

app = FastAPI(
    title="BarberPole API",
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

app.include_router(auth_router)
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
