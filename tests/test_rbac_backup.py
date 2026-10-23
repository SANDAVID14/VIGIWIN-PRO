"""
Pruebas automatizadas de control de acceso (RBAC) y copias de seguridad con SHA-256.
"""
import os
import json
import tempfile
import pytest

from vigiwin.core.database import DatabaseManager
from vigiwin.core.rbac import RBACManager
from vigiwin.core.backup import BackupManager

@pytest.fixture
def temp_env():
    temp_dir = tempfile.mkdtemp()
    db_file = os.path.join(temp_dir, "test_rbac.db")
    db = DatabaseManager(db_file)
    rbac = RBACManager(db)
    backup = BackupManager(db)
    yield db, rbac, backup, temp_dir
    try:
        os.remove(db_file)
        os.rmdir(temp_dir)
    except Exception:
        pass

def test_rbac_authentication_and_permissions(temp_env):
    db, rbac, _, _ = temp_env

    # Login correcto como admin
    assert rbac.login("admin", "admin123") is True
    assert rbac.get_current_role() == "Administrador"
    assert rbac.has_permission("manage_backups") is True

    # Login como operador
    assert rbac.login("operador", "operador123") is True
    assert rbac.get_current_role() == "Operador de Seguridad"
    assert rbac.has_permission("view_live") is True
    assert rbac.has_permission("manage_backups") is False

    # Login fallido
    assert rbac.login("admin", "clave_incorrecta") is False

def test_backup_creation_and_integrity_verification(temp_env):
    db, _, backup, temp_dir = temp_env

    # Añadir dato previo
    db.set_setting("test_custom_key", "valor_123")
    backup_file = os.path.join(temp_dir, "backup_test.json")

    success, msg = backup.create_json_backup(backup_file)
    assert success is True
    assert os.path.exists(backup_file)

    # Validar integridad
    is_valid, val_msg, data = backup.validate_backup_file(backup_file)
    assert is_valid is True
    assert data["settings"]["test_custom_key"] == '"valor_123"'

    # Modificar archivo para simular corrupción
    with open(backup_file, "r+", encoding="utf-8") as f:
        content = f.read()
        corrupted = content.replace("valor_123", "valor_corrupto")
        f.seek(0)
        f.write(corrupted)
        f.truncate()

    is_valid_corr, val_msg_corr, _ = backup.validate_backup_file(backup_file)
    assert is_valid_corr is False
    assert "integridad" in val_msg_corr.lower()

def test_backup_restore(temp_env):
    db, _, backup, temp_dir = temp_env

    db.set_setting("original_setting", 42)
    backup_file = os.path.join(temp_dir, "backup_restore.json")
    backup.create_json_backup(backup_file)

    # Modificar setting
    db.set_setting("original_setting", 999)
    assert db.get_setting("original_setting") == 999

    # Restaurar
    res, msg = backup.restore_from_json(backup_file)
    assert res is True
    assert db.get_setting("original_setting") == 42
