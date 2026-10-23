"""
VIGI-WIN PRO - Módulos Independientes de Detección de Personas y Vehículos
Visión artificial 100% local, sin conexión a Internet ni APIs de pago.
Incluye interruptores independientes, ajuste de sensibilidad, filtrado ROI,
persistencia temporal (debounce) y reglas antispam (cooldown).
"""
import cv2
import time
import numpy as np
from typing import List, Dict, Any, Optional, Tuple

class ObjectDetector:
    STATUS_ACTIVE = "ACTIVADO"
    STATUS_DISABLED = "DESACTIVADO"
    STATUS_PROCESSING = "PROCESANDO"
    STATUS_NO_CAMERA = "SIN_CAMARA"
    STATUS_ERROR = "ERROR"

    def __init__(self, camera_id: str = "CAM_01"):
        self.camera_id = camera_id

        # Interruptores independientes
        self.detect_person_enabled = True
        self.detect_vehicle_enabled = True

        # Sensibilidad (0.1 a 1.0)
        self.person_sensitivity = 0.80  # 80%
        self.vehicle_sensitivity = 0.75 # 75%

        # Zonas de interés (ROI)
        self.person_roi: Optional[Dict[str, int]] = None
        self.vehicle_roi: Optional[Dict[str, int]] = None

        # Tiempos de persistencia (segundos que debe persistir antes de alertar)
        self.person_persistence_sec = 1.0
        self.vehicle_persistence_sec = 1.0

        # Cooldown antispam para evitar inundar con alertas repetitivas de la misma presencia continua
        self.person_cooldown_sec = 15.0
        self.vehicle_cooldown_sec = 15.0

        # Estados temporales
        self._person_first_seen_time: Optional[float] = None
        self._vehicle_first_seen_time: Optional[float] = None
        self._person_last_alert_time = 0.0
        self._vehicle_last_alert_time = 0.0

        # Estado visible de cada módulo
        self.person_status = self.STATUS_ACTIVE
        self.vehicle_status = self.STATUS_ACTIVE

        # Inicializar detector HOG de personas si está disponible en la versión de OpenCV
        if hasattr(cv2, "HOGDescriptor") and hasattr(cv2, "HOGDescriptor_getDefaultPeopleDetector"):
            try:
                self._hog = cv2.HOGDescriptor()
                self._hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
            except Exception:
                self._hog = None
        else:
            self._hog = None

        # Sustractor de fondo para análisis de movimiento y objetos
        self._bg_subtractor = cv2.createBackgroundSubtractorMOG2()

    def set_person_enabled(self, enabled: bool):
        self.detect_person_enabled = enabled
        self.person_status = self.STATUS_ACTIVE if enabled else self.STATUS_DISABLED
        if not enabled:
            self._person_first_seen_time = None

    def set_vehicle_enabled(self, enabled: bool):
        self.detect_vehicle_enabled = enabled
        self.vehicle_status = self.STATUS_ACTIVE if enabled else self.STATUS_DISABLED
        if not enabled:
            self._vehicle_first_seen_time = None

    def set_sensitivities(self, person_sens_pct: int, vehicle_sens_pct: int):
        self.person_sensitivity = max(0.1, min(1.0, person_sens_pct / 100.0))
        self.vehicle_sensitivity = max(0.1, min(1.0, vehicle_sens_pct / 100.0))

    def detect(self, frame: Optional[np.ndarray], stream_state: str = "CONECTADO") -> Dict[str, Any]:
        """Ejecuta la detección de personas y vehículos de forma estrictamente desacoplada."""
        now = time.monotonic()
        results = {
            "persons": [],
            "vehicles": [],
            "trigger_person_alert": False,
            "trigger_vehicle_alert": False,
            "person_alert_data": None,
            "vehicle_alert_data": None,
            "person_status": self.person_status,
            "vehicle_status": self.vehicle_status
        }

        # Comprobar estado de la cámara
        if stream_state in ["DESCONECTADO", "SIN_SENAL", "ERROR"]:
            self.person_status = self.STATUS_NO_CAMERA if self.detect_person_enabled else self.STATUS_DISABLED
            self.vehicle_status = self.STATUS_NO_CAMERA if self.detect_vehicle_enabled else self.STATUS_DISABLED
            results["person_status"] = self.person_status
            results["vehicle_status"] = self.vehicle_status
            return results

        if frame is None or frame.size == 0:
            return results

        h, w = frame.shape[:2]

        # ----------------------------------------------------
        # 1. MÓDULO INDEPENDIENTE DE PERSONAS
        # ----------------------------------------------------
        if self.detect_person_enabled:
            self.person_status = self.STATUS_PROCESSING
            persons_detected = self._detect_persons_in_frame(frame)
            # Filtrar por ROI de personas si está configurado
            if self.person_roi:
                persons_detected = [p for p in persons_detected if self._is_box_in_roi(p["box"], self.person_roi)]

            results["persons"] = persons_detected

            if len(persons_detected) > 0:
                if self._person_first_seen_time is None:
                    self._person_first_seen_time = now

                duration_seen = now - self._person_first_seen_time
                time_since_last_alert = now - self._person_last_alert_time

                # Validar persistencia y antispam
                if duration_seen >= self.person_persistence_sec and time_since_last_alert >= self.person_cooldown_sec:
                    results["trigger_person_alert"] = True
                    results["person_alert_data"] = {
                        "camera_id": self.camera_id,
                        "type": "Persona",
                        "count": len(persons_detected),
                        "confidence": persons_detected[0]["confidence"],
                        "box": persons_detected[0]["box"],
                        "message": f"Persona detectada en {self.camera_id} (Confianza: {int(persons_detected[0]['confidence']*100)}%)"
                    }
                    self._person_last_alert_time = now
            else:
                self._person_first_seen_time = None
            self.person_status = self.STATUS_ACTIVE
        else:
            self.person_status = self.STATUS_DISABLED
            self._person_first_seen_time = None

        # ----------------------------------------------------
        # 2. MÓDULO INDEPENDIENTE DE VEHÍCULOS
        # ----------------------------------------------------
        if self.detect_vehicle_enabled:
            self.vehicle_status = self.STATUS_PROCESSING
            vehicles_detected = self._detect_vehicles_in_frame(frame)
            # Filtrar por ROI de vehículos si está configurado
            if self.vehicle_roi:
                vehicles_detected = [v for v in vehicles_detected if self._is_box_in_roi(v["box"], self.vehicle_roi)]

            results["vehicles"] = vehicles_detected

            if len(vehicles_detected) > 0:
                if self._vehicle_first_seen_time is None:
                    self._vehicle_first_seen_time = now

                duration_seen = now - self._vehicle_first_seen_time
                time_since_last_alert = now - self._vehicle_last_alert_time

                # Validar persistencia y antispam
                if duration_seen >= self.vehicle_persistence_sec and time_since_last_alert >= self.vehicle_cooldown_sec:
                    results["trigger_vehicle_alert"] = True
                    results["vehicle_alert_data"] = {
                        "camera_id": self.camera_id,
                        "type": "Vehículo",
                        "category": vehicles_detected[0].get("category", "Vehículo"),
                        "count": len(vehicles_detected),
                        "confidence": vehicles_detected[0]["confidence"],
                        "box": vehicles_detected[0]["box"],
                        "message": f"Vehículo ({vehicles_detected[0].get('category', 'Auto')}) detectado en {self.camera_id}"
                    }
                    self._vehicle_last_alert_time = now
            else:
                self._vehicle_first_seen_time = None
            self.vehicle_status = self.STATUS_ACTIVE
        else:
            self.vehicle_status = self.STATUS_DISABLED
            self._vehicle_first_seen_time = None

        results["person_status"] = self.person_status
        results["vehicle_status"] = self.vehicle_status
        return results

    def _detect_persons_in_frame(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """Detección de personas mediante HOG (si está disponible) y análisis morfológico de aspecto vertical."""
        persons = []
        h, w = frame.shape[:2]

        if self._hog is not None:
            scale = 0.5
            small = cv2.resize(frame, (0, 0), fx=scale, fy=scale)
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            hit_threshold = (1.0 - self.person_sensitivity) * 0.4
            boxes, weights = self._hog.detectMultiScale(
                gray,
                winStride=(8, 8),
                padding=(8, 8),
                scale=1.05,
                hitThreshold=hit_threshold
            )
            for (bx, by, bw, bh), weight in zip(boxes, weights):
                orig_x = int(bx / scale)
                orig_y = int(by / scale)
                orig_w = int(bw / scale)
                orig_h = int(bh / scale)
                conf = min(0.99, max(0.40, float(weight) + 0.3))
                if orig_h > orig_w * 1.3:
                    persons.append({
                        "box": (orig_x, orig_y, orig_w, orig_h),
                        "confidence": round(conf, 2),
                        "category": "Persona"
                    })

        # Detección morfológica por silueta vertical y movimiento
        if len(persons) == 0:
            fg_mask = self._bg_subtractor.apply(frame)
            contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if 2000 < area < 35000:
                    x, y, bw, bh = cv2.boundingRect(cnt)
                    aspect = bh / float(max(1, bw))
                    if 1.5 < aspect < 4.0 and bh > 55:
                        conf = round(min(0.95, 0.65 + (self.person_sensitivity * 0.2)), 2)
                        persons.append({
                            "box": (x, y, bw, bh),
                            "confidence": conf,
                            "category": "Persona"
                        })
                        break

        return persons

    def _detect_vehicles_in_frame(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """Detección de vehículos por características geométricas horizontales (ancho > alto) y sustracción de fondo."""
        vehicles = []
        h, w = frame.shape[:2]
        fg_mask = self._bg_subtractor.apply(frame)
        # Limpieza morfológica
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        cleaned = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            area = cv2.contourArea(cnt)
            # Vehículos ocupan un área horizontal moderada o grande
            if area > 4500:
                x, y, bw, bh = cv2.boundingRect(cnt)
                aspect = bw / float(bh) # Relación de aspecto horizontal
                
                # Excluir la zona superior del cielo
                if y > h * 0.2:
                    # Clasificación por tamaño y aspecto
                    if 1.2 <= aspect <= 3.2:
                        conf = round(min(0.95, 0.65 + (area / 40000.0) * 0.3), 2)
                        if conf >= (self.vehicle_sensitivity * 0.85):
                            category = "Automóvil"
                            if area > 20000:
                                category = "Camión / Furgoneta"
                            elif bw < 60:
                                category = "Motocicleta"

                            vehicles.append({
                                "box": (x, y, bw, bh),
                                "confidence": conf,
                                "category": category
                            })

        return vehicles

    def _is_box_in_roi(self, box: Tuple[int, int, int, int], roi: Dict[str, int]) -> bool:
        bx, by, bw, bh = box
        rx = roi.get("x", 0)
        ry = roi.get("y", 0)
        rw = roi.get("width", 1000)
        rh = roi.get("height", 1000)
        # Comprobar si el centro del objeto está dentro de la ROI
        cx = bx + bw // 2
        cy = by + bh // 2
        return (rx <= cx <= rx + rw) and (ry <= cy <= ry + rh)
