@echo off
TITLE VIGI-WIN PRO - Compilador Automatico para Windows 10 y 11
echo ======================================================================
echo   VIGI-WIN PRO v1.0 - Compilador y Generador de Ejecutable Windows
echo ======================================================================
echo.

cd /d "%~dp0\.."

echo [1/3] Ejecutando auto-reparador de dependencias e integridad...
python installer\bootstrap.py
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Fallo en la verificacion de dependencias.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [2/3] Compilando con PyInstaller en modo paquete independiente...
pyinstaller --noconfirm VigiWinPro.spec

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] La compilacion con PyInstaller fallo.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [3/3] Compilacion finalizada exitosamente.
echo Ubicacion del ejecutable: dist\VigiWinPro\VigiWinPro.exe
echo.
echo Puede ejecutar la aplicacion directamente o generar el instalador final con Inno Setup.
echo ======================================================================
pause
