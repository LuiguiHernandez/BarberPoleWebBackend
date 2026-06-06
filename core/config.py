from pydantic_settings import BaseSettings, SettingsConfigDict # Importa SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # Base de datos
    DATABASE_URL: str

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

    # Google Gemini IA
    GEMINI_API_KEY: str = ""

    # Google Calendar OAuth2
    GCAL_CLIENT_ID: str = ""
    GCAL_CLIENT_SECRET: str = ""
    GCAL_REDIRECT_URI: str = "http://167.172.145.102:8000/api/gcal/callback"

    # App
    APP_NAME: str = "GestorPro"
    DEBUG: bool = True

    # Cifrado de tokens OAuth (genera con: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    ENCRYPTION_KEY: str = ""

    # Email transaccional — Resend (resend.com)
    # Sin RESEND_API_KEY: los emails solo se imprimen en los logs (modo desarrollo)
    # Con RESEND_API_KEY: se envían emails reales
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = "GestorPro <noreply@gestorpro.app>"

    # Wompi — pasarela de pagos Colombia (obtener en comercios.wompi.co)
    # Sandbox:    pub_stagtest_xxx  /  prv_stagtest_xxx
    # Producción: pub_prod_xxx      /  prv_prod_xxx
    WOMPI_PUBLIC_KEY: str = ""
    WOMPI_PRIVATE_KEY: str = ""
    WOMPI_EVENTS_SECRET: str = ""       # Para verificar firma de webhooks
    WOMPI_INTEGRITY_SECRET: str = ""    # Para generar hash del widget
    WOMPI_PRECIO_CENTS: int = 25000000  # $250.000 COP = 25.000.000 centavos

    # --- LA CORRECCIÓN ESTÁ AQUÍ ---
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"  # Esto le dice a Pydantic: "Si ves algo extra en el .env, ignóralo"
    )

settings = Settings()
# Instancia global del cifrador (se inicializa lazy)
_fernet = None

def get_fernet():
    """Retorna instancia Fernet para cifrar/descifrar tokens OAuth."""
    global _fernet
    if _fernet is None:
        from cryptography.fernet import Fernet
        key = settings.ENCRYPTION_KEY
        if not key:
            # En desarrollo sin clave, generar una temporal (no apta para producción)
            import logging
            logging.getLogger(__name__).warning(
                "[SECURITY] ENCRYPTION_KEY no configurada — usando clave temporal. "
                "Configura ENCRYPTION_KEY en .env para producción."
            )
            key = Fernet.generate_key().decode()
        _fernet = Fernet(key.encode() if isinstance(key, str) else key)
    return _fernet

def encrypt_token(token: str) -> str:
    """Cifra un token OAuth antes de guardarlo en BD."""
    if not token:
        return token
    return get_fernet().encrypt(token.encode()).decode()

def decrypt_token(token: str) -> str:
    """Descifra un token OAuth al leerlo de BD."""
    if not token:
        return token
    try:
        return get_fernet().decrypt(token.encode()).decode()
    except Exception:
        # Si falla el descifrado, el token puede estar en texto plano (migración)
        return token
