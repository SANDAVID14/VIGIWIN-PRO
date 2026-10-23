"""
VIGI-WIN PRO - Pruebas exhaustivas de RBAC (Control de Acceso Basado en Roles)
Verifica CRUD de usuarios en SQLite, matriz de permisos dinámica,
conmutación en tiempo real y registro de auditoría.
"""
import os
import tempfile
import pytest

from vigiwin.core.database import DatabaseManager
from vigiwin.core.rbac import RBACManager


@pytest.fixture
def rbac_env():
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_rbac_full.db")
    db = DatabaseManager(db_path)
    rbac = RBACManager(db)
    yield db, rbac
    try:
        os.remove(db_path)
        os.rmdir(temp_dir)
    except Exception:
        pass


def test_initial_seeded_users(rbac_env):
    db, rbac = rbac_env
    users = rbac.get_users()
    usernames = [u["username"] for u in users]
    assert "admin" in usernames
    assert "operador" in usernames
    assert "auditor" in usernames

    # Login exitoso de los usuarios iniciales
    assert rbac.login("admin", "admin123") is True
    assert rbac.get_current_role() == "Administrador"

    assert rbac.login("operador", "operador123") is True
    assert rbac.get_current_role() == "Operador de Seguridad"

    assert rbac.login("auditor", "auditor123") is True
    assert rbac.get_current_role() == "Auditor"


def test_user_creation_and_validation(rbac_env):
    db, rbac = rbac_env

    # 1. Validación de usuario vacío
    ok, msg = rbac.create_user("", "clave123", "Operador de Seguridad")
    assert ok is False
    assert "vacío" in msg.lower()

    # 2. Validación de contraseña corta
    ok, msg = rbac.create_user("nuevo_usr", "123", "Operador de Seguridad")
    assert ok is False
    assert "4 caracteres" in msg.lower()

    # 3. Validación de rol inválido
    ok, msg = rbac.create_user("nuevo_usr", "clave123", "RolFalso")
    assert ok is False

    # 4. Creación válida
    ok, msg = rbac.create_user("guardia1", "secreto123", "Operador de Seguridad")
    assert ok is True
    assert "exitosamente" in msg.lower()

    # 5. Prevención de usuario duplicado
    ok, msg = rbac.create_user("guardia1", "otra_clave", "Auditor")
    assert ok is False
    assert "ya existe" in msg.lower()

    # 6. Login del nuevo usuario
    assert rbac.login("guardia1", "secreto123") is True
    assert rbac.get_current_role() == "Operador de Seguridad"


def test_change_password_and_role(rbac_env):
    db, rbac = rbac_env

    # Crear usuario
    rbac.create_user("analista", "claveOriginal1", "Auditor")

    # Cambiar contraseña
    ok, msg = rbac.change_password("analista", "claveNueva2")
    assert ok is True
    assert rbac.login("analista", "claveOriginal1") is False
    assert rbac.login("analista", "claveNueva2") is True

    # Cambiar rol de analista a Operador de Seguridad
    ok, msg = rbac.change_role("analista", "Operador de Seguridad")
    assert ok is True
    assert rbac.login("analista", "claveNueva2") is True
    assert rbac.get_current_role() == "Operador de Seguridad"

    # Intentar degradar al único admin del sistema
    rbac.switch_user("admin")
    ok, msg = rbac.change_role("admin", "Auditor")
    assert ok is False
    assert "único administrador" in msg.lower()


def test_delete_user_protections(rbac_env):
    db, rbac = rbac_env
    rbac.create_user("temporal", "temp1234", "Auditor")

    # Intentar eliminar al usuario activo actual
    rbac.switch_user("temporal")
    ok, msg = rbac.delete_user("temporal")
    assert ok is False
    assert "sesión actualmente activa" in msg.lower()

    # Conmutar a admin y eliminar el usuario temporal
    rbac.switch_user("admin")
    ok, msg = rbac.delete_user("temporal")
    assert ok is True

    # Intentar eliminar al único administrador
    ok, msg = rbac.delete_user("admin")
    assert ok is False
    assert ("sesión actualmente activa" in msg.lower() or "único administrador" in msg.lower())


def test_dynamic_permission_matrix(rbac_env):
    db, rbac = rbac_env

    # Admin tiene acceso total
    rbac.switch_user("admin")
    assert rbac.has_permission("configure_cameras") is True
    assert rbac.has_permission("build_installer") is True
    assert rbac.has_permission("view_live") is True

    # Operador no tiene build_installer por defecto
    rbac.switch_user("operador")
    assert rbac.has_permission("view_live") is True
    assert rbac.has_permission("build_installer") is False

    # Personalizar matriz: otorgar build_installer al Operador
    rbac.set_permission("Operador de Seguridad", "build_installer", True)
    assert rbac.has_permission("build_installer") is True

    # Revocar permiso otorgado
    rbac.set_permission("Operador de Seguridad", "build_installer", False)
    assert rbac.has_permission("build_installer") is False

    # Restablecer valores de fábrica
    rbac.reset_permissions_to_default()
    assert rbac.has_permission("build_installer") is False


def test_session_switch_and_audit_logging(rbac_env):
    db, rbac = rbac_env

    notified_users = []
    rbac.on_user_changed = lambda u: notified_users.append(u.get("username"))

    # Conmutar de admin a operador
    assert rbac.switch_user("operador") is True
    assert rbac.get_current_username() == "operador"
    assert "operador" in notified_users

    # Conmutar a auditor
    assert rbac.switch_user("auditor") is True
    assert rbac.get_current_username() == "auditor"
    assert "auditor" in notified_users

    # Verificar que los logs de auditoría registraron las conmutaciones
    logs = db.get_audit_logs(limit=20)
    actions = [l["action"] for l in logs]
    assert "Conmutación Rápida de Sesión" in actions


def test_user_cargo_and_status_management(rbac_env):
    db, rbac = rbac_env

    # 1. Crear usuario con cargo y estado activo
    ok, msg = rbac.create_user("supervisor1", "sup1234", "Operador", cargo="Supervisor de Turno Noche", is_active=1)
    assert ok is True
    user = db.get_user("supervisor1")
    assert user is not None
    assert user["cargo"] == "Supervisor de Turno Noche"
    assert user["is_active"] == 1
    assert user["role"] == "Operador"

    # Login exitoso
    assert rbac.login("supervisor1", "sup1234") is True
    assert rbac.get_current_cargo() == "Supervisor de Turno Noche"

    # Volver a admin
    rbac.switch_user("admin")

    # 2. Modificar cargo y contraseña
    ok, msg = rbac.update_user("supervisor1", role="Operador", cargo="Jefe de Seguridad Patrimonial", is_active=1, new_password="nueva_clave_123")
    assert ok is True
    assert rbac.login("supervisor1", "nueva_clave_123") is True
    assert rbac.get_current_cargo() == "Jefe de Seguridad Patrimonial"

    # 3. Desactivar usuario
    rbac.switch_user("admin")
    ok, msg = rbac.update_user("supervisor1", role="Operador", cargo="Jefe de Seguridad Patrimonial", is_active=0)
    assert ok is True

    # El usuario desactivado no debe poder iniciar sesión ni conmutar
    assert rbac.login("supervisor1", "nueva_clave_123") is False
    assert rbac.switch_user("supervisor1") is False

    # 4. Protección: No se puede desactivar a sí mismo
    rbac.switch_user("admin")
    ok, msg = rbac.update_user("admin", role="Administrador", cargo="Admin", is_active=0)
    assert ok is False
    assert "desactivar" in msg.lower() and "activa" in msg.lower()

    # 5. Protección: No se puede degradar o desactivar al único Administrador
    ok, msg = rbac.update_user("admin", role="Operador", cargo="Operador", is_active=1)
    assert ok is False
    assert "administrador activo" in msg.lower()

    # 6. Protección: No se puede eliminar al usuario de la sesión activa
    ok, msg = rbac.delete_user("admin")
    assert ok is False
    assert "activa" in msg.lower()

    # 7. Protección: Estando en otra sesión activa, no se puede eliminar al único Administrador
    rbac.current_user = {"username": "superuser_temp", "role": "Administrador", "cargo": "Admin", "is_active": 1}
    ok, msg = rbac.delete_user("admin")
    assert ok is False
    assert "administrador activo" in msg.lower()


def test_camera_detection_configuration(rbac_env):
    db, rbac = rbac_env

    # Verificar que existe la cámara inicial
    cams = db.get_cameras()
    assert len(cams) >= 1
    cam_id = cams[0]["id"]

    # Actualizar parámetros de detección de IA
    ok = db.update_camera_detection(
        camera_id=cam_id,
        detect_person=0,
        detect_vehicle=1,
        person_sens=90,
        vehicle_sens=65,
        max_open_sec=45
    )
    assert ok is True

    # Verificar persistencia en base de datos
    updated_cam = db.get_camera(cam_id)
    assert updated_cam["detect_person"] == 0
    assert updated_cam["detect_vehicle"] == 1
    assert updated_cam["person_sensitivity"] == 90
    assert updated_cam["vehicle_sensitivity"] == 65
    assert updated_cam["door_max_open_sec"] == 45


def test_company_branding_persistence(rbac_env):
    db, rbac = rbac_env

    # Permiso de branding para Administrador
    rbac.switch_user("admin")
    assert rbac.has_permission("company_branding") is True

    # Permiso denegado para Operador y Auditor
    rbac.switch_user("operador")
    assert rbac.has_permission("company_branding") is False
    rbac.switch_user("auditor")
    assert rbac.has_permission("company_branding") is False

    # Guardar nombre de empresa y logo en configuración
    db.set_setting("company_name", "Corporación VigiSegura S.A.")
    db.set_setting("company_logo_path", "C:/recursos/logo_corporativo.png")

    assert db.get_setting("company_name") == "Corporación VigiSegura S.A."
    assert db.get_setting("company_logo_path") == "C:/recursos/logo_corporativo.png"
