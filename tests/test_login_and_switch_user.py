"""
Pruebas Automatizadas de la Pantalla de Login y Conmutación de Usuario en Caliente.
Valida autenticación obligatoria y cambio de sesión sin salir de la aplicación.
"""
import os
import pytest
from PySide6.QtWidgets import QApplication, QLineEdit

from vigiwin.core.database import DatabaseManager
from vigiwin.core.rbac import RBACManager
from vigiwin.ui.login_dialog import LoginDialog
from vigiwin.ui.main_window import VigiWinMainWindow


@pytest.fixture(scope="module")
def app_rbac_env():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance() or QApplication([])
    db = DatabaseManager()
    rbac_mgr = RBACManager(db)
    yield db, rbac_mgr, app


def test_login_dialog_admin_success(app_rbac_env):
    """Verifica que el diálogo de login permite autenticación exitosa como Administrador."""
    _, rbac_mgr, _ = app_rbac_env
    dlg = LoginDialog(rbac_mgr, is_switch_user=False)
    dlg.txt_username.setText("admin")
    dlg.txt_password.setText("admin123")

    dlg._do_login()

    assert dlg.result() == 1 # QDialog.Accepted
    assert rbac_mgr.get_current_username() == "admin"
    assert rbac_mgr.get_current_role() == "Administrador"
    assert dlg.lbl_error.text() == ""


def test_login_dialog_invalid_password(app_rbac_env):
    """Verifica que contraseñas erróneas son rechazadas con mensaje descriptivo."""
    _, rbac_mgr, _ = app_rbac_env
    initial_user = rbac_mgr.get_current_username()

    dlg = LoginDialog(rbac_mgr, is_switch_user=False)
    dlg.txt_username.setText("admin")
    dlg.txt_password.setText("clave_incorrecta")

    dlg._do_login()

    assert dlg.result() == 0 # No aceptado
    assert "incorrectas" in dlg.lbl_error.text().lower()
    assert rbac_mgr.get_current_username() == initial_user


def test_login_dialog_quick_chips(app_rbac_env):
    """Verifica que los chips de acceso rápido rellenan correctamente las credenciales."""
    _, rbac_mgr, _ = app_rbac_env
    dlg = LoginDialog(rbac_mgr, is_switch_user=False)

    # Autorellenar con auditor
    dlg._fill_credentials("auditor", "auditor123")
    assert dlg.txt_username.text() == "auditor"
    assert dlg.txt_password.text() == "auditor123"

    dlg._do_login()
    assert dlg.result() == 1
    assert rbac_mgr.get_current_username() == "auditor"
    assert rbac_mgr.get_current_role() == "Auditor"


def test_switch_user_inside_main_window(app_rbac_env):
    """Verifica el cambio de usuario sin salir de la aplicación y actualización dinámica de permisos."""
    _, rbac_mgr, _ = app_rbac_env

    # 1. Iniciar sesión como Admin
    rbac_mgr.login("admin", "admin123")
    win = VigiWinMainWindow(rbac_manager=rbac_mgr)
    assert win.btn_switch_user is not None
    assert "admin" in win.lbl_user_badge.text()
    assert win.btn_nav_code.isEnabled() is True
    assert win.btn_nav_tests.isEnabled() is True

    # 2. Conmutar usuario a Operador mediante LoginDialog
    switch_dlg = LoginDialog(rbac_mgr, is_switch_user=True, parent=win)
    switch_dlg.txt_username.setText("operador")
    switch_dlg.txt_password.setText("operador123")
    switch_dlg._do_login()

    assert switch_dlg.result() == 1
    assert rbac_mgr.get_current_username() == "operador"

    # 3. La ventana debe reflejar los nuevos permisos de Operador sin cerrarse
    assert "operador" in win.lbl_user_badge.text()
    assert "Operador" in win.lbl_user_badge.text()
    assert win.btn_nav_code.isEnabled() is False # Bloqueado para Operador
    assert win.btn_nav_tests.isEnabled() is False # Bloqueado para Operador

    # 4. Conmutar de vuelta a Admin
    admin_dlg = LoginDialog(rbac_mgr, is_switch_user=True, parent=win)
    admin_dlg.txt_username.setText("admin")
    admin_dlg.txt_password.setText("admin123")
    admin_dlg._do_login()

    assert rbac_mgr.get_current_username() == "admin"
    assert win.btn_nav_code.isEnabled() is True
    assert win.btn_nav_tests.isEnabled() is True

    win.close()
