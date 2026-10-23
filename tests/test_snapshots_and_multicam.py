"""
Pruebas Automatizadas de las Nuevas Funcionalidades:
1. Captura Automática de Instantáneas Forenses (Snapshots JPG) y Persistencia en DB/CSV.
2. Modo Multi-Cámara Cuadrícula (Grid 2x2 / 1x1) y Procesamiento Simultáneo.
"""
import os
import pytest
import numpy as np

from vigiwin.core.config import get_snapshots_dir
from vigiwin.core.database import DatabaseManager
from vigiwin.core.audio import AudioManager
from vigiwin.vision.camera_manager import CameraManager

@pytest.fixture(scope="module")
def qapp_env():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    db = DatabaseManager()
    audio = AudioManager()
    cam_mgr = CameraManager(db)
    yield db, cam_mgr, audio, app

def test_snapshots_directory_and_file_creation(qapp_env):
    """Verifica que el directorio de snapshots existe y que save_snapshot genera un JPG válido."""
    db, cam_mgr, _, _ = qapp_env
    sdir = get_snapshots_dir()
    assert sdir.exists()

    # Generar un fotograma sintético o capturar de la cámara activa
    snap_path = cam_mgr.save_snapshot("CAM_01", "TEST_PUERTA_ALARMA")
    assert snap_path is not None
    assert os.path.exists(snap_path)
    assert os.path.getsize(snap_path) > 1000 # Más de 1 KB

    # Validar cabecera JPEG (bytes 0xFF, 0xD8)
    with open(snap_path, "rb") as f:
        header = f.read(2)
        assert header == b"\xff\xd8"

def test_database_snapshot_path_logging_and_csv(qapp_env, tmp_path):
    """Verifica que la columna snapshot_path persiste en SQLite y se exporta en el CSV."""
    db, cam_mgr, _, _ = qapp_env
    sdir = get_snapshots_dir()
    dummy_snap = str(sdir / "test_snapshot_forense.jpg")
    with open(dummy_snap, "wb") as f:
        f.write(b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 200)

    eid = db.log_event(
        camera="CAM_01",
        event_type="Persona",
        message="Detección de prueba forense",
        priority="Media",
        details={"confianza": 0.88},
        snapshot_path=dummy_snap
    )
    assert eid > 0

    events = db.get_events(limit=5)
    target = next((e for e in events if e["id"] == eid), None)
    assert target is not None
    assert target["snapshot_path"] == dummy_snap

    # Exportar CSV
    csv_file = str(tmp_path / "export_test.csv")
    count = db.export_events_csv(csv_file)
    assert count > 0

    with open(csv_file, "r", encoding="utf-8-sig") as f:
        content = f.read()
        assert "Evidencia Snapshot" in content
        assert "test_snapshot_forense.jpg" in content

def test_camera_manager_multicam_processing(qapp_env):
    """Verifica que CameraManager procesa fotogramas de cualquier cámara (para modo cuadrícula)."""
    db, cam_mgr, _, _ = qapp_env
    cam_mgr.start_all()

    # Procesar CAM_01
    res1 = cam_mgr.process_camera_frame("CAM_01")
    assert res1.get("frame") is not None
    assert "door_result" in res1
    assert "obj_result" in res1

    # Procesar CAM_02 si existe
    if "CAM_02" in cam_mgr.streams:
        res2 = cam_mgr.process_camera_frame("CAM_02")
        assert res2.get("frame") is not None

def test_surveillance_tab_view_modes(qapp_env):
    """Verifica la conmutación entre modo 1x1 y modo cuadrícula 2x2 en la interfaz."""
    db, cam_mgr, audio, _ = qapp_env
    from vigiwin.ui.surveillance_tab import SurveillanceTab

    tab = SurveillanceTab(cam_mgr, db, audio)
    assert tab.view_mode == "1x1"
    assert tab.video_stack.currentIndex() == 0

    # Cambiar a 2x2
    tab._set_view_mode("2x2")
    assert tab.view_mode == "2x2"
    assert tab.video_stack.currentIndex() == 1
    assert len(tab.grid_tiles) >= 1

    # Cambiar de vuelta a 1x1
    tab._set_view_mode("1x1")
    assert tab.view_mode == "1x1"
    assert tab.video_stack.currentIndex() == 0

def test_history_tab_evidence_ui(qapp_env):
    """Verifica que la pestaña de historial muestra la columna de evidencia y actualiza el panel."""
    db, cam_mgr, _, _ = qapp_env
    from vigiwin.ui.history_tab import HistoryTab

    htab = HistoryTab(db)
    assert htab.table.columnCount() == 8
    header_title = htab.table.horizontalHeaderItem(7).text()
    assert "Evidencia" in header_title

    # Seleccionar la primera fila si existe
    if htab.table.rowCount() > 0:
        htab.table.selectRow(0)
        assert htab.selected_event is not None
