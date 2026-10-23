"""
Pruebas automatizadas de los detectores independientes de personas y vehículos.
"""
import numpy as np
import pytest
from vigiwin.vision.object_detector import ObjectDetector

def test_independent_switches():
    det = ObjectDetector("CAM_01")
    assert det.detect_person_enabled is True
    assert det.detect_vehicle_enabled is True

    # Desactivar personas de forma independiente
    det.set_person_enabled(False)
    assert det.detect_person_enabled is False
    assert det.detect_vehicle_enabled is True
    assert det.person_status == ObjectDetector.STATUS_DISABLED
    assert det.vehicle_status == ObjectDetector.STATUS_ACTIVE

    # Desactivar vehículos de forma independiente
    det.set_vehicle_enabled(False)
    assert det.detect_person_enabled is False
    assert det.detect_vehicle_enabled is False

    # Reactivar personas únicamente
    det.set_person_enabled(True)
    assert det.detect_person_enabled is True
    assert det.detect_vehicle_enabled is False

def test_sensitivities_and_roi():
    det = ObjectDetector("CAM_01")
    det.set_sensitivities(person_sens_pct=90, vehicle_sens_pct=60)
    assert det.person_sensitivity == 0.90
    assert det.vehicle_sensitivity == 0.60

    det.person_roi = {"x": 50, "y": 50, "width": 200, "height": 300}
    # Box dentro del ROI
    assert det._is_box_in_roi((80, 100, 40, 80), det.person_roi) is True
    # Box fuera del ROI
    assert det._is_box_in_roi((350, 200, 50, 100), det.person_roi) is False

def test_detection_on_frame():
    det = ObjectDetector("CAM_01")
    # Fotograma neutro sintético
    frame = np.full((360, 640, 3), 30, dtype=np.uint8)
    results = det.detect(frame, "CONECTADO")
    assert "persons" in results
    assert "vehicles" in results
    assert isinstance(results["persons"], list)
    assert isinstance(results["vehicles"], list)

def test_signal_loss_status():
    det = ObjectDetector("CAM_01")
    frame = np.full((360, 640, 3), 30, dtype=np.uint8)
    results = det.detect(frame, "SIN_SENAL")
    assert results["person_status"] == ObjectDetector.STATUS_NO_CAMERA
    assert results["vehicle_status"] == ObjectDetector.STATUS_NO_CAMERA
