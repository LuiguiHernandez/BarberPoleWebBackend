from sqlalchemy.orm import Session
from fastapi import HTTPException
from models.all_models import Usuario, Negocio, Horario, DiaSemana
from schemas.all_schemas import RegisterRequest, LoginRequest, TokenResponse
from core.security import hash_password, verify_password, create_access_token, create_refresh_token


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def register(self, data: RegisterRequest) -> TokenResponse:
        # Validaciones básicas
        if len(data.password) < 6:
            raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres")
        if not data.nombre.strip():
            raise HTTPException(status_code=400, detail="El nombre es obligatorio")
        if not data.nombre_negocio.strip():
            raise HTTPException(status_code=400, detail="El nombre del negocio es obligatorio")

        # Email único
        if self.db.query(Usuario).filter(Usuario.email == data.email.lower().strip()).first():
            raise HTTPException(status_code=400, detail="Este email ya está registrado")

        # Generar slug único para el negocio
        import re
        base_slug = re.sub(r'[^a-z0-9]+', '-', data.nombre_negocio.lower().strip()).strip('-')
        slug = base_slug
        contador = 1
        while self.db.query(Negocio).filter(Negocio.slug == slug).first():
            slug = f"{base_slug}-{contador}"
            contador += 1

        # Aplicar colores del tema según el tipo de negocio
        from core.temas import TEMAS
        from datetime import datetime, timedelta, timezone
        tema = TEMAS.get(data.tipo_negocio or "general", TEMAS["general"])

        # Trial expira en 30 días desde el registro
        trial_expira = datetime.now(timezone.utc) + timedelta(days=30)

        usuario = Usuario(
            nombre=data.nombre.strip(),
            email=data.email.lower().strip(),
            password_hash=hash_password(data.password),
            rol="cliente",
            activo=True,
        )
        self.db.add(usuario)
        self.db.flush()

        negocio = Negocio(
            usuario_id=usuario.id,
            nombre=data.nombre_negocio.strip(),
            slug=slug,
            tipo_negocio=data.tipo_negocio or "general",
            telefono=data.telefono_negocio,
            color_primario=tema.get("color_primario", "#00A86B"),
            color_secundario=tema.get("color_secundario", "#E8F5EE"),
            color_fondo=tema.get("color_fondo", "#FFFFFF"),
            color_texto=tema.get("color_texto", "#111827"),
            plan="trial",
            plan_expira_en=trial_expira,
        )
        self.db.add(negocio)
        self.db.flush()

        # Horarios por defecto: lunes a sábado 9am-6pm, domingo cerrado
        dias_laborales = {
            DiaSemana.lunes, DiaSemana.martes, DiaSemana.miercoles,
            DiaSemana.jueves, DiaSemana.viernes, DiaSemana.sabado,
        }
        for dia in DiaSemana:
            self.db.add(Horario(
                negocio_id=negocio.id,
                dia=dia,
                abierto=dia in dias_laborales,
                hora_inicio="09:00",
                hora_fin="18:00",
            ))

        self.db.commit()
        self.db.refresh(usuario)

        # Tokens de sesión
        token         = create_access_token({"sub": str(usuario.id)})
        refresh_token = create_refresh_token({"sub": str(usuario.id)})

        # Enviar email de bienvenida con verificación (async — no bloquea la respuesta)
        try:
            import asyncio
            from routers.password_reset import crear_token_verificacion
            from services.email_service import send_email, html_bienvenida
            from core.config import settings
            token_verificacion = crear_token_verificacion(usuario.id)
            link = f"{settings.FRONTEND_URL.rstrip('/')}/verify-email?token={token_verificacion}"
            asyncio.create_task(send_email(
                to=usuario.email,
                subject=f"¡Bienvenido a GestorPro, {usuario.nombre}!",
                html=html_bienvenida(usuario.nombre, negocio.nombre, link),
            ))
        except Exception:
            pass  # El email es opcional — no bloquea el registro

        return TokenResponse(
            access_token=token,
            refresh_token=refresh_token,
            usuario_nombre=usuario.nombre,
            negocio_nombre=negocio.nombre,
            negocio_slug=negocio.slug,
        )

    def login(self, data: LoginRequest) -> TokenResponse:
        usuario = self.db.query(Usuario).filter(Usuario.email == data.email).first()
        if not usuario or not verify_password(data.password, usuario.password_hash):
            raise HTTPException(status_code=401, detail="Credenciales incorrectas")

        token         = create_access_token({"sub": str(usuario.id)})
        refresh_token = create_refresh_token({"sub": str(usuario.id)})
        negocio = usuario.negocio
        return TokenResponse(
            access_token=token,
            refresh_token=refresh_token,
            usuario_nombre=usuario.nombre,
            negocio_nombre=negocio.nombre if negocio else None,
            negocio_slug=negocio.slug if negocio else None,
        )

    def refresh(self, refresh_token: str) -> TokenResponse:
        """Genera un nuevo access_token a partir de un refresh_token válido."""
        from core.security import decode_token
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Token inválido")

        user_id = payload.get("sub")
        usuario = self.db.query(Usuario).filter(Usuario.id == int(user_id)).first()
        if not usuario:
            raise HTTPException(status_code=401, detail="Usuario no encontrado")

        new_access  = create_access_token({"sub": str(usuario.id)})
        new_refresh = create_refresh_token({"sub": str(usuario.id)})
        negocio = usuario.negocio
        return TokenResponse(
            access_token=new_access,
            refresh_token=new_refresh,
            usuario_nombre=usuario.nombre,
            negocio_nombre=negocio.nombre if negocio else None,
            negocio_slug=negocio.slug if negocio else None,
        )
