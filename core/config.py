from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Base de datos
    DATABASE_URL = str

    # Seguridad
    SECRET_KEY: str = "cambia-esta-clave"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080

    # CORS
    FRONTEND_URL: str = "http://localhost:5173"

    # Evolution API
    EVOLUTION_API_URL: str = "http://167.172.145.102:8080"
    EVOLUTION_API_KEY: str = ""
    EVOLUTION_INSTANCE: str = "Prueba"

    # n8n
    N8N_URL: str = "http://167.172.145.102:5678"
    N8N_WEBHOOK_URL: str = "http://167.172.145.102:5678/webhook/whatsapp"
    N8N_WEBHOOK_SECRET: str = ""

    # App
    APP_NAME: str = "BarberPole"
    DEBUG: bool = True

    class Config:
        env_file = ".env"


settings = Settings()
