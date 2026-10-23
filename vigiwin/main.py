"""
VIGI-WIN PRO - Punto de Entrada Principal
Lanza la aplicación de escritorio en Windows con soporte de escala DPI universal (Windows 10/11),
ajuste automático de pantalla y gestión de excepciones.
"""
import sys
import os
from pathlib import Path

# Configuración de variables de entorno para escalado DPI de Qt antes de iniciar QApplication
os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
os.environ.setdefault("QT_SCALE_FACTOR_ROUNDING_POLICY", "PassThrough")

# Habilitar soporte de alta resolución DPI nativo en Windows 10 y Windows 11 (Per-Monitor V2)
if sys.platform == "win32":
    try:
        import ctypes
        # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        try:
            # Fallback para versiones anteriores: PROCESS_PER_MONITOR_DPI_AWARE = 2
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from vigiwin.ui.main_window import VigiWinMainWindow


def get_app_icon() -> QIcon:
    """Carga el icono vanguardista de la aplicación."""
    base_dir = Path(__file__).resolve().parent
    icon_png = base_dir / "assets" / "icon.png"
    icon_ico = base_dir / "assets" / "icon.ico"
    if icon_png.exists():
        return QIcon(str(icon_png))
    elif icon_ico.exists():
        return QIcon(str(icon_ico))
    return QIcon()


def main():
    if hasattr(Qt, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("VIGI-WIN PRO")
    app.setOrganizationName("VigiWinPro")
    app.setWindowIcon(get_app_icon())

    # Autenticación inicial obligatoria mediante LoginDialog
    from vigiwin.core.database import DatabaseManager
    from vigiwin.core.rbac import RBACManager
    from vigiwin.ui.login_dialog import LoginDialog

    db = DatabaseManager()
    rbac_mgr = RBACManager(db)

    # Solicitar credenciales al inicio
    if "--no-login" not in sys.argv and os.environ.get("VIGIWIN_NO_LOGIN") != "1":
        login_dlg = LoginDialog(rbac_mgr, is_switch_user=False)
        if not login_dlg.exec():
            sys.exit(0)

    window = VigiWinMainWindow(rbac_manager=rbac_mgr)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

