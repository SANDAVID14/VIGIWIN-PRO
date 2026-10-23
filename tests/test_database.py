"""
Pruebas automatizadas de la base de datos SQLite y persistencia.
"""
import os
import pytest
import tempfile
from vigiwin.core.database import DatabaseManager

@pytest.fixture
def temp_db():
    temp_dir = tempfile.mkdtemp()
    db_file = os.path.join(temp_dir, "test_vigiwin.db")
    db = DatabaseManager(db_file)
    yield db
    try:
        os.remove(db_file)
        os.rmdir(temp_dir)
    except Exception:
        pass

def test_database_initialization(temp_db):
    cams = temp_db.get_cameras()
    assert len(cams) >= 1
    assert cams[0]["id"] == "CAM_01"

def test_event_logging_and_confirmation(temp_db):
    eid = temp_db.log_event("CAM_01", "Alerta Puerta", "Puerta abierta más de 60 segundos", "Alta")
    assert eid > 0

    events = temp_db.get_events(limit=10)
    assert len(events) >= 1
    assert events[0]["confirmed"] == 0

    # Confirmar evento
    success = temp_db.confirm_event(eid, "Operador_Test")
    assert success is True

    events_after = temp_db.get_events(limit=10)
    assert events_after[0]["confirmed"] == 1
    assert events_after[0]["confirmed_by"] == "Operador_Test"

def test_settings_persistence(temp_db):
    temp_db.set_setting("door_max_open_seconds", 120)
    val = temp_db.get_setting("door_max_open_seconds")
    assert val == 120

def test_camera_management(temp_db):
    new_cam = {
        "id": "CAM_RTSP_02",
        "name": "Portón Norte RTSP",
        "source_type": "rtsp",
        "source_url": "rtsp://admin:1234@192.168.1.55:554/live",
        "perspective": "lateral",
        "door_max_open_sec": 45,
        "detect_person": 1,
        "detect_vehicle": 0,
        "person_sensitivity": 85,
        "vehicle_sensitivity": 70,
        "is_active": 1
    }
    temp_db.save_camera(new_cam)
    cam = temp_db.get_camera("CAM_RTSP_02")
    assert cam is not None
    assert cam["name"] == "Portón Norte RTSP"
    assert cam["perspective"] == "lateral"
    assert cam["door_max_open_sec"] == 45
    assert cam["detect_vehicle"] == 0

def test_csv_export(temp_db):
    temp_db.log_event("CAM_01", "Persona", "Persona detectada", "Media")
    csv_file = os.path.join(tempfile.gettempdir(), "test_export.csv")
    count = temp_db.export_events_csv(csv_file)
    assert count >= 1
    assert os.path.exists(csv_file)
    with open(csv_file, "r", encoding="utf-8-sig") as f:
        content = f.read()
        assert "CAM_01" in content
        assert "Persona detectada" in content
    os.remove(csv_file)
