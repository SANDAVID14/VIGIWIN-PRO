"""
VIGI-WIN PRO - Detector Inteligente de Estado de Puertas, Portones y Talanqueras
Vigilancia visual con calibración, perspectiva frontal y lateral,
validación temporal, umbral de variación del 10% y temporizador de tiempo real.
"""
import cv2
import time
import numpy as np
from typing import Dict, Any, Optional, Tuple

class DoorDetector:
    STATE_CLOSED = "CERRADO"
    STATE_OPEN = "ABIERTO"
    STATE_ALARM = "ALARMA_CRITICA"
    STATE_UNCERTAIN = "INCERTIDUMBRE"

    def __init__(self, camera_id: str = "CAM_01", max_open_seconds: int = 60, variation_threshold_pct: float = 10.0):
        self.camera_id = camera_id
        self.max_open_seconds = max_open_seconds
        self.variation_threshold_pct = variation_threshold_pct # 10% obligatorio
        self.perspective = "frontal" # "frontal" o "lateral"

        # ROI de la puerta (por defecto centrado en resolución 640x360)
        self.roi = {"x": 250, "y": 80, "width": 140, "height": 200}
        self.reference_features: Optional[np.ndarray] = None
        self.reference_gray: Optional[np.ndarray] = None

        # Estado del detector
        self.current_state = self.STATE_CLOSED
        self.variation_pct = 0.0
        self.door_open_start_time: Optional[float] = None
        self.elapsed_open_seconds = 0.0
        self.alarm_triggered = False

        # Validación temporal para supresión de falsos positivos
        self._pending_state = self.STATE_CLOSED
        self._consecutive_frames = 0
        self.required_consecutive_frames = 4 # ~130ms a 30 FPS

        # Historial de cierre para aviso
        self.just_closed = False
        self.total_last_open_duration = 0.0

    def set_roi(self, x: int, y: int, width: int, height: int):
        self.roi = {
            "x": max(0, x),
            "y": max(0, y),
            "width": max(10, width),
            "height": max(10, height)
        }
        self.reference_features = None
        self.reference_gray = None

    def set_perspective(self, perspective: str):
        if perspective in ["frontal", "lateral"]:
            self.perspective = perspective

    def calibrate_closed_reference(self, frame: np.ndarray):
        """Almacena la captura actual de la puerta cerrada como plantilla de referencia."""
        if frame is None:
            return
        roi_img = self._extract_roi(frame)
        if roi_img is not None and roi_img.size > 0:
            gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
            # Suavizado Gaussiano para reducir ruido de sensor
            self.reference_gray = cv2.GaussianBlur(gray, (5, 5), 0)
            # Extraer mapa de bordes Canny como firma estructural de la puerta cerrada
            self.reference_features = cv2.Canny(self.reference_gray, 50, 150)
            self.current_state = self.STATE_CLOSED
            self.door_open_start_time = None
            self.alarm_triggered = False
            self.elapsed_open_seconds = 0.0

    def _extract_roi(self, frame: np.ndarray) -> Optional[np.ndarray]:
        h, w = frame.shape[:2]
        x1 = max(0, min(w - 1, self.roi["x"]))
        y1 = max(0, min(h - 1, self.roi["y"]))
        x2 = max(x1 + 10, min(w, x1 + self.roi["width"]))
        y2 = max(y1 + 10, min(h, y1 + self.roi["height"]))
        if x2 <= x1 or y2 <= y1:
            return None
        return frame[y1:y2, x1:x2]

    def process_frame(self, frame: Optional[np.ndarray]) -> Dict[str, Any]:
        """Procesa un fotograma y devuelve el estado actual y métricas."""
        now = time.monotonic()
        self.just_closed = False

        # Si el fotograma no es válido o está corrupto: INCERTIDUMBRE
        if frame is None or frame.size == 0:
            return self._build_result(self.STATE_UNCERTAIN, 0.0, "Sin fotograma disponible")

        # Comprobación de calidad básica (evitar imágenes completamente negras o saturadas)
        mean_brightness = np.mean(frame)
        if mean_brightness < 5.0 or mean_brightness > 250.0:
            return self._build_result(self.STATE_UNCERTAIN, 0.0, "Condiciones lumínicas no aptas o cámara tapada")

        roi_img = self._extract_roi(frame)
        if roi_img is None:
            return self._build_result(self.STATE_UNCERTAIN, 0.0, "Error al extraer ROI")

        # Si no hay calibración previa, auto-calibrar con el primer fotograma
        if self.reference_gray is None:
            self.calibrate_closed_reference(frame)
            return self._build_result(self.STATE_CLOSED, 0.0, "Calibración inicial establecida")

        # Calcular variación estructural respecto al estado cerrado
        current_gray = cv2.GaussianBlur(cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY), (5, 5), 0)
        if current_gray.shape != self.reference_gray.shape:
            current_gray = cv2.resize(current_gray, (self.reference_gray.shape[1], self.reference_gray.shape[0]))

        # 1. Diferencia absoluta de intensidad
        diff = cv2.absdiff(self.reference_gray, current_gray)
        _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
        pixel_variation_ratio = np.count_nonzero(thresh) / float(thresh.size)

        # 2. Correlación de bordes estructurales
        edges = cv2.Canny(current_gray, 50, 150)
        if self.reference_features is not None:
            edge_diff = cv2.absdiff(self.reference_features, edges)
            edge_variation_ratio = np.count_nonzero(edge_diff) / float(edge_diff.size)
        else:
            edge_variation_ratio = pixel_variation_ratio

        # Ponderación según perspectiva
        if self.perspective == "lateral":
            # En lateral, el movimiento angular provoca mayor cambio en bordes verticales
            raw_variation = (pixel_variation_ratio * 0.4 + edge_variation_ratio * 0.6)
        else:
            raw_variation = (pixel_variation_ratio * 0.5 + edge_variation_ratio * 0.5)

        # Escalar a porcentaje
        calculated_pct = min(100.0, raw_variation * 180.0)
        self.variation_pct = round(calculated_pct, 1)

        # Comprobación de confianza: contraste y visibilidad
        contrast = float(np.std(current_gray))
        mean_val = float(np.mean(current_gray))
        if contrast < 1.0 and (mean_val < 15.0 or mean_val > 240.0):
            raw_detected_state = self.STATE_UNCERTAIN
        elif self.variation_pct >= self.variation_threshold_pct:
            raw_detected_state = self.STATE_OPEN
        else:
            raw_detected_state = self.STATE_CLOSED

        # Validación temporal para filtrar ruido o parpadeos breves
        if raw_detected_state == self._pending_state:
            self._consecutive_frames += 1
        else:
            self._pending_state = raw_detected_state
            self._consecutive_frames = 1

        # Si se confirma el estado durante los fotogramas requeridos
        if self._consecutive_frames >= self.required_consecutive_frames:
            previous_committed_state = self.current_state
            self.current_state = raw_detected_state

            # Lógica de transición de estados y temporizador en tiempo real
            if self.current_state in [self.STATE_OPEN, self.STATE_ALARM]:
                if self.door_open_start_time is None:
                    # Puerta acaba de abrirse
                    self.door_open_start_time = now
                    self.alarm_triggered = False
                    self.elapsed_open_seconds = 0.0

                self.elapsed_open_seconds = now - self.door_open_start_time

                # Comprobar si superó el umbral crítico (60 seg por defecto)
                if self.elapsed_open_seconds >= self.max_open_seconds:
                    self.current_state = self.STATE_ALARM
                    self.alarm_triggered = True

            elif self.current_state == self.STATE_CLOSED:
                if previous_committed_state in [self.STATE_OPEN, self.STATE_ALARM] and self.door_open_start_time is not None:
                    # La puerta se acaba de cerrar
                    self.just_closed = True
                    self.total_last_open_duration = round(now - self.door_open_start_time, 1)

                # Reiniciar temporizador
                self.door_open_start_time = None
                self.elapsed_open_seconds = 0.0
                self.alarm_triggered = False

            elif self.current_state == self.STATE_UNCERTAIN:
                # En caso de incertidumbre, mantener el temporizador si ya estaba abierta
                if self.door_open_start_time is not None:
                    self.elapsed_open_seconds = now - self.door_open_start_time

        return self._build_result(self.current_state, self.variation_pct)

    def _build_result(self, state: str, variation_pct: float, extra_msg: str = "") -> Dict[str, Any]:
        return {
            "camera_id": self.camera_id,
            "state": state,
            "variation_pct": variation_pct,
            "threshold_pct": self.variation_threshold_pct,
            "elapsed_seconds": round(self.elapsed_open_seconds, 1),
            "max_open_seconds": self.max_open_seconds,
            "is_alarm": (state == self.STATE_ALARM),
            "just_closed": self.just_closed,
            "total_open_duration": self.total_last_open_duration,
            "perspective": self.perspective,
            "roi": self.roi,
            "extra_message": extra_msg
        }

    def reset_timer(self):
        self.door_open_start_time = None
        self.elapsed_open_seconds = 0.0
        self.alarm_triggered = False
        self.current_state = self.STATE_CLOSED
