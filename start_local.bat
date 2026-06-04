@echo off
REM Arrancar el servidor de desarrollo de GestorPro
title GestorPro Backend - Local
call venv\Scripts\activate.bat
echo.
echo  GestorPro Backend corriendo en http://localhost:8000
echo  Docs API en http://localhost:8000/docs
echo  Presiona CTRL+C para detener
echo.
uvicorn main:app --reload --port 8000
