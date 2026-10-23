"""
Pruebas unitarias para el motor de actualización vigiwin.core.updater
Verifica conexión con GitHub, detección de cambios y preservación estricta de configuración de usuario.
"""
import pytest
import os
import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import patch, MagicMock

from vigiwin.core.updater import SystemUpdater, GITHUB_REPO_URL
from vigiwin.core.database import DatabaseManager


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = DatabaseManager(db_path=path)
    yield db
    import gc
    gc.collect()
    try:
        if os.path.exists(path):
            os.remove(path)
    except PermissionError:
        pass


def test_updater_init():
    updater = SystemUpdater()
    assert updater.repo_url == GITHUB_REPO_URL
    assert updater.root_dir.exists()


def test_updater_is_git_repository():
    updater = SystemUpdater()
    assert updater.is_git_repository() is True


def test_updater_check_updates_mock_up_to_date():
    updater = SystemUpdater()
    with patch.object(updater, "run_git_command") as mock_git:
        # Mock remote -v
        mock_git.side_effect = [
            MagicMock(returncode=0, stdout="origin https://github.com/SANDAVID14/VIGIWIN-PRO.git (fetch)\n"),  # remote -v
            MagicMock(returncode=0, stdout=""),  # fetch
            MagicMock(returncode=0, stdout="a1b2c3d4\n"),  # rev-parse HEAD
            MagicMock(returncode=0, stdout="a1b2c3d4\n"),  # rev-parse origin/master
        ]
        res = updater._check_git_updates()
        assert res["success"] is True
        assert res["has_updates"] is False
        assert res["local_commit"] == "a1b2c3d4"


def test_updater_check_updates_mock_changes_available():
    updater = SystemUpdater()
    with patch.object(updater, "run_git_command") as mock_git:
        mock_git.side_effect = [
            MagicMock(returncode=0, stdout="origin https://github.com/SANDAVID14/VIGIWIN-PRO.git (fetch)\n"),  # remote -v
            MagicMock(returncode=0, stdout=""),  # fetch
            MagicMock(returncode=0, stdout="11111111\n"),  # rev-parse HEAD
            MagicMock(returncode=0, stdout="22222222\n"),  # rev-parse origin/master
            MagicMock(returncode=0, stdout="22222222 - Actualización de seguridad (hace 1 hora) <admin>\n"),  # log
            MagicMock(returncode=0, stdout="vigiwin/ui/admin_tab.py\nvigiwin/main.py\n"),  # diff
        ]
        res = updater._check_git_updates()
        assert res["success"] is True
        assert res["has_updates"] is True
        assert res["local_commit"] == "11111111"
        assert res["remote_commit"] == "22222222"
        assert len(res["commits"]) == 1
        assert "vigiwin/ui/admin_tab.py" in res["changed_files"]


def test_updater_preserves_user_configuration(temp_db):
    """Verifica que apply_updates no altera la base de datos ni las configuraciones personalizadas del usuario."""
    # 1. Configurar datos personalizados de usuario
    temp_db.set_setting("company_name", "Mi Empresa de Seguridad Personalizada S.A.")
    temp_db.set_setting("door_max_open_seconds", 45)
    temp_db.create_user("operador_nocturno", "hash123", "Operador", "Vigilante Nocturno")

    settings_before = temp_db.get_all_settings()
    users_before = temp_db.get_users()

    updater = SystemUpdater()
    with patch.object(updater, "run_git_command") as mock_git:
        mock_git.side_effect = [
            MagicMock(returncode=0, stdout=""),  # status --porcelain
            MagicMock(returncode=0, stdout="origin https://github.com/SANDAVID14/VIGIWIN-PRO.git (fetch)\n"),  # check_git remote -v
            MagicMock(returncode=0, stdout=""),  # check_git fetch
            MagicMock(returncode=0, stdout="11111111\n"),  # check_git rev-parse HEAD
            MagicMock(returncode=0, stdout="22222222\n"),  # check_git rev-parse origin/master
            MagicMock(returncode=0, stdout=""),  # check_git log
            MagicMock(returncode=0, stdout=""),  # check_git diff
            MagicMock(returncode=0, stdout="Fast-forward\n"),  # merge --ff-only
            MagicMock(returncode=0, stdout="22222222\n"),  # rev-parse HEAD
        ]
        res = updater.apply_updates(db_manager=temp_db)
        assert res["success"] is True
        assert res["new_commit"] == "22222222"

    # 2. Verificar que los ajustes y usuarios del usuario NO se modificaron
    settings_after = temp_db.get_all_settings()
    users_after = temp_db.get_users()

    assert settings_after["company_name"] == "Mi Empresa de Seguridad Personalizada S.A."
    assert settings_after["door_max_open_seconds"] == 45
    assert any(u["username"] == "operador_nocturno" for u in users_after)
