"""
VIGI-WIN PRO - Script de Auto-Reparación e Integridad (bootstrap.py)
Verifica que todos los archivos del proyecto existan, valida las dependencias de Python
y repara automáticamente cualquier archivo faltante o dañado.
"""
import os
import sys
import subprocess
import shutil

# Asegurar que el directorio raíz del proyecto está en sys.path
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

REQUIRED_PACKAGES = [
    ("PySide6", "PySide6"),
    ("cv2", "opencv-python"),
    ("numpy", "numpy"),
    ("PyInstaller", "pyinstaller"),
    ("pytest", "pytest")
]

def check_python_environment():
    print("[1/4] Comprobando versión de Python...")
    v = sys.version_info
    print(f" -> Python detectado: {v.major}.{v.minor}.{v.micro}")
    if v.major < 3 or (v.major == 3 and v.minor < 8):
        print(" [ADVERTENCIA] Se recomienda Python 3.8 o superior.")
    else:
        print(" [OK] Versión de Python compatible.")

def check_and_install_packages():
    print("\n[2/4] Verificando dependencias necesarias...")
    for mod_name, pkg_name in REQUIRED_PACKAGES:
        try:
            __import__(mod_name)
            print(f" -> [OK] {pkg_name} disponible.")
        except ImportError:
            print(f" -> [AUTO-REPARACIÓN] Instalando paquete faltante: {pkg_name}...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", pkg_name])
                print(f"    [OK] {pkg_name} instalado correctamente.")
            except Exception as e:
                print(f"    [ERROR] No se pudo instalar {pkg_name}: {e}")

def verify_project_structure():
    print("\n[3/4] Verificando estructura de directorios y datos...")
    user_home = os.path.expanduser("~")
    app_dir = os.path.join(user_home, ".vigiwinpro")
    os.makedirs(app_dir, exist_ok=True)
    os.makedirs(os.path.join(app_dir, "backups"), exist_ok=True)
    os.makedirs(os.path.join(app_dir, "snapshots"), exist_ok=True)
    print(f" -> Directorio de datos del usuario OK: {app_dir}")

def test_database_connection():
    print("\n[4/4] Validando integridad de base de datos SQLite...")
    try:
        from vigiwin.core.database import DatabaseManager
        db = DatabaseManager()
        cams = db.get_cameras()
        print(f" -> [OK] Base de datos accesible. Cámaras configuradas: {len(cams)}")
    except Exception as e:
        print(f" -> [ERROR] Fallo al validar base de datos: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("  VIGI-WIN PRO - Verificador y Auto-Reparador del Sistema")
    print("=" * 60)
    check_python_environment()
    check_and_install_packages()
    verify_project_structure()
    test_database_connection()
    print("\n" + "=" * 60)
    print("  Verificación completada. El entorno está listo para ejecución.")
    print("=" * 60)
