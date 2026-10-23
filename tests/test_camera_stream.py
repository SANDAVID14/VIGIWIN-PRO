"""
Pruebas automatizadas del motor de captura y flujo de vídeo (CameraStream).
"""
import time
import numpy as np
import pytest
from vigiwin.vision.camera_stream import CameraStream

def test_simulation_stream_lifecycle():
    stream = CameraStream(camera_id="CAM_SIM_01", source_type="simulation")
    stream.start()
    assert stream.running is True

    # Esperar que genere fotogramas
    time.sleep(0.15)
    ret, frame, state = stream.read_frame()
    assert ret is True
    assert frame is not None
    assert frame.shape == (360, 640, 3)
    assert state == CameraStream.STATE_CONNECTED

    stream.stop()
    assert stream.running is False

def test_synthetic_door_toggle():
    stream = CameraStream(camera_id="CAM_SIM_02", source_type="simulation")
    stream.set_simulation_door_open(True)
    assert stream.sim_door_open_pct == 1.0

    frame_open = stream._generate_synthetic_frame()
    assert frame_open is not None

    stream.set_simulation_door_open(False)
    assert stream.sim_door_open_pct == 0.0

    frame_closed = stream._generate_synthetic_frame()
    assert frame_closed is not None

    # Los fotogramas deben ser numéricamente distintos
    diff = np.sum(np.abs(frame_open.astype(int) - frame_closed.astype(int)))
    assert diff > 1000
