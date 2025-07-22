@echo off
:: Script para activar el entorno virtual y instalar dependencias

:: Comprueba si Python está instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python no está instalado. Por favor, instálalo antes de continuar.
    exit /b
)

:: Crea un entorno virtual si no existe
if not exist "qgis_agent_env" (
    echo Creando el entorno virtual...
    python -m venv qgis_agent_env
)


source qgis_agent_env/bin/activate
call qgis_agent_env/bin/activate


::# Si estás en un entorno de desarrollo donde QGIS ya está instalado, puedes necesitar configurar PYTHONPATH. # Ejemplo (Linux/macOS): 
::export
:: PYTHONPATH=$PYTHONPATH:/usr/share/qgis/python:/usr/share/qgis/python/plugins

