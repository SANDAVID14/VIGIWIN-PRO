"""
Pruebas automatizadas del detector de estado de puertas y portones (DoorDetector).
"""
import numpy as np
import pytest
import time
from vigiwin.vision.door_detector import DoorDetector

def create_synthetic_door_frame(is_open=False, variation_level=0.0):
    """Crea un fotograma sintético 640x360 con una puerta."""
    frame = np.full((360, 640, 3), 40, dtype=np.uint8)
    dx, dy, dw, dh = 250, 80, 140, 200
    if not is_open:
        # Puerta cerrada con patrón uniforme
        frame[dy:dy+dh, dx:dx+dw] = (120, 120, 120)
    else:
        # Puerta abierta con hueco oscuro y hoja desplazada según variation_level
        frame[dy:dy+dh, dx:dx+dw] = (15, 15, 15)
        # Hoja restante
        rem_w = int(dw * (1.0 - min(1.0, variation_level)))
        if rem_w > 0:
            frame[dy:dy+dh, dx:dx+rem_w] = (120, 120, 120)
    return frame

def test_door_initial_calibration():
    detector = DoorDetector("CAM_01", max_open_seconds=60, variation_threshold_pct=10.0)
    closed_frame = create_synthetic_door_frame(is_open=False)
    detector.calibrate_closed_reference(closed_frame)
    assert detector.reference_gray is not None

    res = detector.process_frame(closed_frame)
    assert res["state"] == DoorDetector.STATE_CLOSED
    assert res["variation_pct"] <= 5.0

def test_door_open_variation_threshold_10pct():
    detector = DoorDetector("CAM_01", max_open_seconds=60, variation_threshold_pct=10.0)
    closed_frame = create_synthetic_door_frame(is_open=False)
    detector.calibrate_closed_reference(closed_frame)

    # Crear fotograma con variación del 30% (superior al 10% obligatorio)
    open_frame = create_synthetic_door_frame(is_open=True, variation_level=0.30)

    # Pasar los fotogramas necesarios para la validación temporal (debounce)
    res = None
    for _ in range(detector.required_consecutive_frames + 2):
        res = detector.process_frame(open_frame)

    assert res["state"] == DoorDetector.STATE_OPEN
    assert res["variation_pct"] >= 10.0
    assert res["elapsed_seconds"] >= 0.0

def test_door_closure_detection_and_reset():
    detector = DoorDetector("CAM_01", max_open_seconds=60, variation_threshold_pct=10.0)
    closed_frame = create_synthetic_door_frame(is_open=False)
    detector.calibrate_closed_reference(closed_frame)

    open_frame = create_synthetic_door_frame(is_open=True, variation_level=0.50)
    for _ in range(detector.required_consecutive_frames + 2):
        detector.process_frame(open_frame)

    assert detector.current_state == DoorDetector.STATE_OPEN

    # Ahora vuelve a cerrarse la puerta
    closure_results = []
    for _ in range(detector.required_consecutive_frames + 2):
        closure_results.append(detector.process_frame(closed_frame))

    assert any(r["just_closed"] is True for r in closure_results)
    assert closure_results[-1]["state"] == DoorDetector.STATE_CLOSED
    assert closure_results[-1]["elapsed_seconds"] == 0.0

def test_door_critical_alarm_threshold():
    # Probar con umbral corto para prueba unitaria
    detector = DoorDetector("CAM_01", max_open_seconds=1, variation_threshold_pct=10.0)
    closed_frame = create_synthetic_door_frame(is_open=False)
    detector.calibrate_closed_reference(closed_frame)

    open_frame = create_synthetic_door_frame(is_open=True, variation_level=0.60)
    for _ in range(detector.required_consecutive_frames + 1):
        detector.process_frame(open_frame)

    # Esperar que transcurra el tiempo crítico en tiempo real
    time.sleep(1.1)

    res = detector.process_frame(open_frame)
    assert res["state"] == DoorDetector.STATE_ALARM
    assert res["is_alarm"] is True

def test_door_uncertainty_handling():
    detector = DoorDetector("CAM_01", max_open_seconds=60, variation_threshold_pct=10.0)
    # Fotograma completamente negro (cámara tapada o sin luz)
    black_frame = np.zeros((360, 640, 3), dtype=np.uint8)
    res = detector.process_frame(black_frame)
    assert res["state"] == DoorDetector.STATE_UNCERTAIN
