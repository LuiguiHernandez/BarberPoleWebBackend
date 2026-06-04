@echo off
REM ═══════════════════════════════════════════════════════════════════════════
REM  GestorPro — Setup Local (Windows)
REM  Ejecutar UNA SOLA VEZ para configurar el entorno de desarrollo
REM ═══════════════════════════════════════════════════════════════════════════

echo.
echo  GestorPro - Configurando entorno local...
echo  ─────────────────────────────────────────

REM 1. Crear entorno virtual con Python 3.13
echo [1/4] Creando entorno virtual...
"C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python313\python.exe" -m venv venv
if errorlevel 1 (
    echo ERROR: No se encontro Python 3.13. Instalar desde python.org
    pause
    exit /b 1
)

REM 2. Activar entorno e instalar dependencias
echo [2/4] Instalando dependencias...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo ERROR instalando dependencias
    pause
    exit /b 1
)

REM 3. Copiar .env si no existe
echo [3/4] Configurando variables de entorno...
if not exist .env (
    copy .env.local .env
    echo   Archivo .env creado desde .env.local
) else (
    echo   .env ya existe, no se sobreescribio
)

REM 4. Verificar conexion a la base de datos
echo [4/4] Verificando conexion a la BD...
python -c "from core.database import engine; conn = engine.connect(); conn.close(); print('  BD OK')" 2>nul
if errorlevel 1 (
    echo   ADVERTENCIA: No se pudo conectar a la BD. Verifica DATABASE_URL en .env
)

echo.
echo  ✓ Setup completado.
echo.
echo  Para iniciar el servidor:
echo    venv\Scripts\activate
echo    uvicorn main:app --reload --port 8000
echo.
pause
