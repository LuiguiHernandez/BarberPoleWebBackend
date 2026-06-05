from sqlalchemy.orm import Session
from fastapi import HTTPException
from models.all_models import Usuario, Negocio, Horario, DiaSemana
from schemas.all_schemas import RegisterRequest, LoginRequest, TokenResponse
from core.security import hash_password, verify_password, create_access_token, create_refresh_token


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def register(self, data: RegisterRequest) -> TokenResponse:
        if self.db.query(Usuario).filter(Usuario.email == data.email).first():
            raise HTTPException(status_code=400, detail="El email ya está registrado")

        usuario = Usuario(
            nombre=data.nombre,
            email=data.email,
            password_hash=hash_password(data.password),
        )
        self.db.add(usuario)
        self.db.flush()

        negocio = Negocio(
            usuario_id=usuario.id,
            nombre=data.nombre_negocio,
            slug=data.nombre_negocio.lower().replace(" ", "-"),
        )
        self.db.add(negocio)
        self.db.flush()

        dias_laborales = {
            DiaSemana.lunes, DiaSemana.martes, DiaSemana.miercoles,
            DiaSemana.jueves, DiaSemana.viernes, DiaSemana.sabado,
        }
        for dia in DiaSemana:
            horario = Horario(
                negocio_id=negocio.id,
                dia=dia,
                abierto=dia in dias_laborales,
                hora_inicio="09:00",
                hora_fin="18:00",
            )
            self.db.add(horario)

        self.db.commit()
        self.db.refresh(usuario)

        token         = create_access_token({"sub": str(usuario.id)})
        refresh_token = create_refresh_token({"sub": str(usuario.id)})
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
