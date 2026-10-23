"""
VIGI-WIN PRO - Punto de Entrada Principal
Lanza la aplicación de escritorio en Windows con soporte de escala DPI y gestión de excepciones.
"""
import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from vigiwin.ui.main_window import VigiWinMainWindow

def main():
    # Habilitar soporte de alta resolución DPI en Windows 10/11
    if hasattr(Qt, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("VIGI-WIN PRO")
    app.setOrganizationName("VigiWinPro")

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
