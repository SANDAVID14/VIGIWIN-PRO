"""
VIGI-WIN PRO - Motor de Captura y Flujo de Vídeo Multi-Cámara
Soporta cámaras USB, flujos RTSP sobre TCP (para DVR/NVR y cámaras IP),
archivos de vídeo local y generador sintético para pruebas sin hardware.
"""
import os
import cv2
import time
import math
import numpy as np
import threading
from typing import Optional, Tuple, Dict, Any

# Forzar TCP en FFmpeg para RTSP y evitar pérdida de cuadros por UDP
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"

class CameraStream:
    STATE_DISCONNECTED = "DESCONECTADO"
    STATE_CONNECTING = "CONECTANDO"
    STATE_CONNECTED = "CONECTADO"
    STATE_SIGNAL_LOST = "SIN_SENAL"
    STATE_ERROR = "ERROR"

    def __init__(self, camera_id: str = "CAM_01", source_type: str = "simulation", source_url: str = "0", name: str = "Cámara 01"):
        self.camera_id = camera_id
        self.source_type = source_type
        self.source_url = source_url
        self.name = name

        self.running = False
        self.cap: Optional[cv2.VideoCapture] = None
        self.thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()

        self.current_frame: Optional[np.ndarray] = None
        self.state = self.STATE_DISCONNECTED
        self.last_frame_time = 0.0
        self.fps = 0.0
        self._frame_count = 0
        self._fps_timer = time.time()

        # Variables para simulación sintética interactiva
        self.sim_door_open_pct = 0.0     # 0.0 = cerrada, 1.0 = completamente abierta
        self.sim_person_present = True
        self.sim_vehicle_present = True
        self.sim_perspective = "frontal" # "frontal" o "lateral"
        self._sim_tick = 0

    def start(self):
        if self.running:
            return
        self.running = True
        if self.source_type == "simulation":
            self.state = self.STATE_CONNECTED
            self.current_frame = self._generate_synthetic_frame()
        else:
            self.state = self.STATE_CONNECTING
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.5)
        self._release_capture()
        self.state = self.STATE_DISCONNECTED

    def _release_capture(self):
        with self.lock:
            if self.cap:
                try:
                    self.cap.release()
                except Exception:
                    pass
                self.cap = None

    def _open_capture(self) -> bool:
        if self.source_type == "simulation":
            self.state = self.STATE_CONNECTED
            return True

        self._release_capture()
        try:
            url = self.source_url
            if self.source_type == "webcam":
                idx = int(url) if url.isdigit() else 0
                self.cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW if os.name == 'nt' else cv2.CAP_ANY)
            elif self.source_type == "rtsp":
                # RTSP con transporte TCP
                self.cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
                if self.cap:
                    self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
            else: # archivo
                self.cap = cv2.VideoCapture(url)

            if self.cap and self.cap.isOpened():
                self.state = self.STATE_CONNECTED
                return True
            else:
                self.state = self.STATE_ERROR
                return False
        except Exception as e:
            print(f"[STREAM] Error al abrir cámara {self.camera_id}: {e}")
            self.state = self.STATE_ERROR
            return False

    def _capture_loop(self):
        retry_delay = 2.0
        while self.running:
            if self.source_type == "simulation":
                frame = self._generate_synthetic_frame()
                with self.lock:
                    self.current_frame = frame
                    self.last_frame_time = time.time()
                    self._update_fps()
                time.sleep(0.033) # ~30 FPS
                continue

            if not self.cap or not self.cap.isOpened():
                if not self._open_capture():
                    time.sleep(retry_delay)
                    continue

            ret, frame = self.cap.read()
            if ret and frame is not None:
                with self.lock:
                    self.current_frame = frame
                    self.last_frame_time = time.time()
                    self.state = self.STATE_CONNECTED
                    self._update_fps()
            else:
                # Pérdida de señal o fin de flujo
                with self.lock:
                    self.state = self.STATE_SIGNAL_LOST
                time.sleep(1.0)
                self._open_capture()

    def _update_fps(self):
        self._frame_count += 1
        now = time.time()
        elapsed = now - self._fps_timer
        if elapsed >= 1.0:
            self.fps = self._frame_count / elapsed
            self._frame_count = 0
            self._fps_timer = now

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray], str]:
        with self.lock:
            # Comprobar si ha transcurrido demasiado tiempo sin fotogramas
            if self.running and self.source_type != "simulation":
                if time.time() - self.last_frame_time > 3.0:
                    self.state = self.STATE_SIGNAL_LOST

            if self.current_frame is not None:
                return True, self.current_frame.copy(), self.state
            return False, None, self.state

    # --- Generador Sintético Realista para Pruebas Locales ---
    def set_simulation_door_open(self, is_open: bool):
        self.sim_door_open_pct = 1.0 if is_open else 0.0

    def set_simulation_door_pct(self, pct: float):
        self.sim_door_open_pct = max(0.0, min(1.0, pct))

    def _generate_synthetic_frame(self) -> np.ndarray:
        self._sim_tick += 1
        w, h = 640, 360
        # Fondo oscuro de vigilancia
        frame = np.full((h, w, 3), 18, dtype=np.uint8)

        # Suelo y perspectiva
        cv2.rectangle(frame, (0, 240), (w, h), (28, 32, 40), -1)
        cv2.line(frame, (0, 240), (w, 240), (50, 60, 75), 1)

        # Rejilla suave de referencia
        for x in range(0, w, 40):
            cv2.line(frame, (x, 0), (x, h), (24, 28, 35), 1)
        for y in range(0, h, 40):
            cv2.line(frame, (0, y), (w, y), (24, 28, 35), 1)

        # Dibujar Puerta / Portón / Talanquera según perspectiva
        if self.sim_perspective == "frontal":
            # Puerta frontal en el centro (x: 250..390, y: 90..270)
            door_x, door_y, door_w, door_h = 260, 90, 120, 180
            # Marco exterior de la puerta
            cv2.rectangle(frame, (door_x - 6, door_y - 6), (door_x + door_w + 6, door_y + door_h), (70, 80, 95), 3)

            # Hueco interior oscuro si está abierta
            cv2.rectangle(frame, (door_x, door_y), (door_x + door_w, door_y + door_h), (8, 10, 14), -1)

            # Hoja de la puerta que se desplaza / gira según sim_door_open_pct
            # Si cerrada: ancho completo. Si abierta: se reduce el ancho visible simulando apertura batiente/corrediza
            visible_w = int(door_w * (1.0 - self.sim_door_open_pct * 0.85))
            leaf_color = (60, 70, 85) if self.sim_door_open_pct < 0.1 else (90, 45, 45)
            cv2.rectangle(frame, (door_x, door_y), (door_x + visible_w, door_y + door_h), leaf_color, -1)
            cv2.rectangle(frame, (door_x, door_y), (door_x + visible_w, door_y + door_h), (120, 140, 160), 2)

            # Manilla o detalles de la puerta
            if visible_w > 20:
                cv2.circle(frame, (door_x + visible_w - 12, door_y + door_h // 2), 4, (180, 200, 220), -1)

        else: # lateral
            # Puerta en perspectiva lateral angulada
            pts_closed = np.array([[120, 80], [180, 120], [180, 280], [120, 260]], np.int32)
            cv2.polylines(frame, [pts_closed], True, (70, 80, 95), 2)
            # Desplazamiento si abre
            shift_x = int(self.sim_door_open_pct * 45)
            shift_y = int(self.sim_door_open_pct * 20)
            pts_leaf = np.array([
                [120 + shift_x, 80 - shift_y],
                [180 + shift_x, 120 - shift_y],
                [180 + shift_x, 280 - shift_y],
                [120 + shift_x, 260 - shift_y]
            ], np.int32)
            cv2.fillPoly(frame, [pts_leaf], (60, 70, 85) if self.sim_door_open_pct < 0.1 else (90, 45, 45))
            cv2.polylines(frame, [pts_leaf], True, (120, 140, 160), 2)

        # Dibujar Persona en movimiento oscilante si está activa
        if self.sim_person_present:
            px = int(140 + math.sin(self._sim_tick * 0.03) * 50)
            py = 180
            # Cabeza
            cv2.circle(frame, (px + 15, py + 12), 10, (180, 190, 200), -1)
            # Torso
            cv2.rectangle(frame, (px + 5, py + 24), (px + 25, py + 55), (140, 150, 165), -1)
            # Piernas
            cv2.line(frame, (px + 10, py + 55), (px + 8, py + 85), (100, 110, 120), 3)
            cv2.line(frame, (px + 20, py + 55), (px + 22, py + 85), (100, 110, 120), 3)

        # Dibujar Vehículo si está activo
        if self.sim_vehicle_present:
            vx = int(430 + math.cos(self._sim_tick * 0.02) * 25)
            vy = 210
            # Carrocería
            cv2.rectangle(frame, (vx, vy + 20), (vx + 110, vy + 55), (80, 110, 160), -1)
            cv2.rectangle(frame, (vx + 20, vy), (vx + 85, vy + 22), (90, 125, 180), -1)
            # Ventanas
            cv2.rectangle(frame, (vx + 25, vy + 4), (vx + 50, vy + 18), (170, 200, 220), -1)
            cv2.rectangle(frame, (vx + 55, vy + 4), (vx + 80, vy + 18), (170, 200, 220), -1)
            # Ruedas
            cv2.circle(frame, (vx + 25, vy + 55), 10, (20, 20, 20), -1)
            cv2.circle(frame, (vx + 85, vy + 55), 10, (20, 20, 20), -1)

        return frame
