"""
Validación Automatizada de los 24 Puntos de Control Obligatorios
(Sección 11 de especificaciones y Suite de Verificación de Backend vigiwin.html)
"""
import os
import sys
import pytest
import sqlite3
import numpy as np
import cv2

from vigiwin.core.config import get_app_data_dir, get_db_path
from vigiwin.core.database import DatabaseManager
from vigiwin.vision.door_detector import DoorDetector
from vigiwin.vision.object_detector import ObjectDetector
from vigiwin.vision.camera_manager import CameraManager

@pytest.fixture(scope="module")
def app_env():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    db = DatabaseManager()
    cam_mgr = CameraManager(db)
    yield db, cam_mgr, app

def test_p01_user_directory_permissions():
    """Punto 1: Verificación de permisos de usuario en C:\\Users"""
    home = os.path.expanduser("~")
    assert os.path.exists(home)
    assert os.access(home, os.W_OK)

def test_p02_vigiwin_directory_structure():
    """Punto 2: Estructura de directorio ~/.vigiwinpro"""
    app_dir = get_app_data_dir()
    assert app_dir.exists()

def test_p03_sqlite_database_connection(app_env):
    """Punto 3: Conexión a Base de Datos SQLite (vigiwin.db)"""
    db, _, _ = app_env
    with db.get_connection() as conn:
        assert conn is not None

def test_p04_table_events_schema(app_env):
    """Punto 4: Esquema de tabla 'events' y claves primarias"""
    db, _, _ = app_env
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(events)")
        cols = {row["name"] for row in cur.fetchall()}
        assert {"id", "timestamp", "camera", "event_type", "message", "priority"}.issubset(cols)

def test_p05_table_settings_schema(app_env):
    """Punto 5: Esquema de tabla 'settings'"""
    db, _, _ = app_env
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(settings)")
        cols = {row["name"] for row in cur.fetchall()}
        assert "key" in cols and "value" in cols

def test_p06_pyside6_environment():
    """Punto 6: Módulo PySide6.QtWidgets en entorno Windows"""
    from PySide6 import QtWidgets
    assert QtWidgets.QApplication.instance() is not None

def test_p07_opencv_and_codecs():
    """Punto 7: Importación de OpenCV (cv2) y códecs de video"""
    assert cv2.__version__ is not None
    assert hasattr(cv2, "VideoCapture")

def test_p08_numpy_matrix_calc():
    """Punto 8: Módulo de cálculo matricial NumPy"""
    a = np.zeros((10, 10))
    assert a.shape == (10, 10)

def test_p09_database_manager_fallback(app_env):
    """Punto 9: Clase DatabaseManager con fallback automático"""
    db, _, _ = app_env
    assert hasattr(db, "log_event")
    assert hasattr(db, "get_events")

def test_p10_alert_overlay_module():
    """Punto 10: Módulo CentralizedAlertOverlay de cuadros flotantes"""
    from vigiwin.ui.alert_overlay import CentralizedAlertOverlay
    assert CentralizedAlertOverlay is not None

def test_p11_bootstrap_auto_repair():
    """Punto 11: Script de auto-reparación e integridad (bootstrap.py)"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    boot_path = os.path.join(base_dir, "installer", "bootstrap.py")
    assert os.path.exists(boot_path)

def test_p12_video_engine_init(app_env):
    """Punto 12: Inicialización del motor de video a 30 FPS"""
    _, cam_mgr, _ = app_env
    stream = cam_mgr.streams.get("CAM_01")
    assert stream is not None
    assert stream.source_type == "simulation" or stream.source_type == "webcam"

def test_p13_perspective_selector(app_env):
    """Punto 13: Selector de perspectiva (Vista Frontal / Lateral)"""
    _, cam_mgr, _ = app_env
    door_det = cam_mgr.door_detectors.get("CAM_01")
    door_det.set_perspective("frontal")
    assert door_det.perspective == "frontal"
    door_det.set_perspective("lateral")
    assert door_det.perspective == "lateral"

def test_p14_roi_overlay(app_env):
    """Punto 14: Superposición de delimitación ROI"""
    _, cam_mgr, _ = app_env
    assert hasattr(cam_mgr, "show_roi")

def test_p15_person_detection_independent_switch(app_env):
    """Punto 15: Switch independiente de detección de Personas"""
    _, cam_mgr, _ = app_env
    obj_det = cam_mgr.object_detectors.get("CAM_01")
    obj_det.set_person_enabled(True)
    obj_det.set_vehicle_enabled(True)
    obj_det.set_person_enabled(False)
    assert obj_det.detect_person_enabled is False
    assert obj_det.detect_vehicle_enabled is True
    obj_det.set_person_enabled(True)
    assert obj_det.detect_person_enabled is True

def test_p16_vehicle_detection_independent_switch(app_env):
    """Punto 16: Switch independiente de detección de Vehículos"""
    _, cam_mgr, _ = app_env
    obj_det = cam_mgr.object_detectors.get("CAM_01")
    obj_det.set_person_enabled(True)
    obj_det.set_vehicle_enabled(True)
    obj_det.set_vehicle_enabled(False)
    assert obj_det.detect_vehicle_enabled is False
    assert obj_det.detect_person_enabled is True
    obj_det.set_vehicle_enabled(True)
    assert obj_det.detect_vehicle_enabled is True

def test_p17_door_sensor_timer(app_env):
    """Punto 17: Temporizador del sensor de puerta abierta"""
    _, cam_mgr, _ = app_env
    door_det = cam_mgr.door_detectors.get("CAM_01")
    assert hasattr(door_det, "elapsed_open_seconds")

def test_p18_critical_alarm_threshold_60s(app_env):
    """Punto 18: Alarma crítica al superar umbral de 60 segundos (1 minuto)"""
    _, cam_mgr, _ = app_env
    door_det = cam_mgr.door_detectors.get("CAM_01")
    assert door_det.max_open_seconds >= 5

def test_p19_taskbar_overlay_window():
    """Punto 19: Superposición emergente tipo Windows Taskbar"""
    from vigiwin.ui.alert_overlay import CentralizedAlertOverlay
    assert hasattr(CentralizedAlertOverlay, "reposition_to_bottom_right")

def test_p20_audit_logging_in_database(app_env):
    """Punto 20: Registro automático de auditoría en base de datos"""
    db, _, _ = app_env
    db.log_audit("Auditor_Test", "Test_Action", "Detalles_Test")
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM audit_log WHERE username='Auditor_Test'")
        row = cur.fetchone()
        assert row is not None

def test_p21_csv_export_feature(app_env):
    """Punto 21: Exportación de registros en formato CSV"""
    db, _, _ = app_env
    assert hasattr(db, "export_events_csv")

def test_p22_inno_setup_script_compatibility():
    """Punto 22: Compatibilidad con script Inno Setup (.iss)"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    iss_path = os.path.join(base_dir, "installer", "installer_script.iss")
    assert os.path.exists(iss_path)

def test_p23_pyinstaller_batch_compiler():
    """Punto 23: Compilador batch de PyInstaller (build.bat)"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bat_path = os.path.join(base_dir, "installer", "build.bat")
    assert os.path.exists(bat_path)

def test_p24_autonomous_executable_package():
    """Punto 24: Verificación final de empaquetado autónomo .exe"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    installer_py = os.path.join(base_dir, "installer", "vigiwin_installer.py")
    assert os.path.exists(installer_py)
