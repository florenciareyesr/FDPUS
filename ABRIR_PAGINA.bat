@echo off
setlocal
cd /d "%~dp0"
title FDPUS - Abrir pagina
echo Preparando FDPUS. La primera vez puede tardar unos minutos.
python --version >nul 2>&1
if errorlevel 1 (
 echo No se encontro Python. Instala Python desde https://www.python.org/downloads/windows/
 echo Durante la instalacion marca Add Python to PATH. Luego vuelve a abrir este archivo.
 pause
 exit /b 1
)
if not exist ".venv\Scripts\python.exe" python -m venv .venv
if not exist ".venv\Scripts\python.exe" (
 echo No se pudo preparar Python. Copia este mensaje para solicitar ayuda.
 pause
 exit /b 1
)
".venv\Scripts\python.exe" -c "import flask,waitress" >nul 2>&1
if errorlevel 1 (
 echo Instalando componentes. Se necesita internet solo para esta instalacion.
 ".venv\Scripts\python.exe" -m pip install "Flask>=3.1,<3.2" "waitress>=3,<4"
 if errorlevel 1 (
  echo No se pudieron instalar los componentes. Revisa tu conexion a internet.
  pause
  exit /b 1
 )
)
".venv\Scripts\python.exe" abrir_local.py
if errorlevel 1 (
 echo La aplicacion no pudo iniciarse. Copia el error que aparece arriba.
 pause
)
