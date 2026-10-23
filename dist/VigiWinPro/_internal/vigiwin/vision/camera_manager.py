"""
VIGI-WIN PRO - Orquestador Multi-Cámara
Gestiona la captura simultánea o conmutada de múltiples cámaras (DVR/NVR, IP, USB y Simulador),
coordinando los detectores de puertas y visión artificial para cada canal.
"""
import cv2
import json
from datetime import datetime
import numpy as np
from typing import Dict, Any, Optional, List, Callable

from vigiwin.vision.camera_stream import CameraStream
from vigiwin.vision.door_detector import DoorDetector
from vigiwin.vision.object_detector import ObjectDetector

class CameraManager:
    def __init__(self, db_manager):
        self.db = db_manager
        self.streams: Dict[str, CameraStream] = {}
        self.door_detectors: Dict[str, DoorDetector] = {}
        self.object_detectors: Dict[str, ObjectDetector] = {}

        self.active_camera_id: str = "CAM_01"
        self.show_roi = True

        # Callbacks para notificaciones y alertas
        self.on_door_alarm_callback: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_door_closed_callback: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_person_alert_callback: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_vehicle_alert_callback: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_signal_lost_callback: Optional[Callable[[str], None]] = None

        self._signal_lost_notified = False

        self._load_cameras_from_db()

    def _load_cameras_from_db(self):
        cams = self.db.get_cameras()
        if not cams:
            # Crear cámara por defecto
            cams = [{
                "id": "CAM_01",
                "name": "Entrada Principal / Vehicular",
                "source_type": "simulation",
                "source_url": "0",
                "perspective": "frontal",
                "door_max_open_sec": 60,
                "detect_person": 1,
                "detect_vehicle": 1,
                "person_sensitivity": 80,
                "vehicle_sensitivity": 75
            }]

        for c in cams:
            cid = c["id"]
            stream = CameraStream(
                camera_id=cid,
                source_type=c.get("source_type", "simulation"),
                source_url=c.get("source_url", "0"),
                name=c.get("name", cid)
            )
            door_det = DoorDetector(
                camera_id=cid,
                max_open_seconds=c.get("door_max_open_sec", 60),
                variation_threshold_pct=10.0
            )
            door_det.set_perspective(c.get("perspective", "frontal"))
            if c.get("door_roi"):
                roi = c["door_roi"]
                door_det.set_roi(roi.get("x", 250), roi.get("y", 80), roi.get("width", 140), roi.get("height", 200))

            obj_det = ObjectDetector(camera_id=cid)
            obj_det.set_person_enabled(bool(c.get("detect_person", 1)))
            obj_det.set_vehicle_enabled(bool(c.get("detect_vehicle", 1)))
            obj_det.set_sensitivities(c.get("person_sensitivity", 80), c.get("vehicle_sensitivity", 75))

            self.streams[cid] = stream
            self.door_detectors[cid] = door_det
            self.object_detectors[cid] = obj_det

        if cams:
            self.active_camera_id = cams[0]["id"]

    def start_active(self):
        if self.active_camera_id in self.streams:
            self.streams[self.active_camera_id].start()

    def start_all(self):
        """Inicia todos los flujos de captura registrados para modo cuadrícula multi-cámara."""
        for stream in self.streams.values():
            stream.start()

    def stop_all(self):
        for stream in self.streams.values():
            stream.stop()

    def set_active_camera(self, camera_id: str):
        if camera_id == self.active_camera_id or camera_id not in self.streams:
            return
        if self.active_camera_id in self.streams:
            self.streams[self.active_camera_id].stop()
        self.active_camera_id = camera_id
        self._signal_lost_notified = False
        self.streams[self.active_camera_id].start()

    def add_or_update_camera(self, cam_dict: Dict[str, Any]):
        cid = cam_dict["id"]
        self.db.save_camera(cam_dict)
        if cid in self.streams:
            self.streams[cid].stop()

        stream = CameraStream(
            camera_id=cid,
            source_type=cam_dict.get("source_type", "simulation"),
            source_url=cam_dict.get("source_url", "0"),
            name=cam_dict.get("name", cid)
        )
        door_det = DoorDetector(
            camera_id=cid,
            max_open_seconds=cam_dict.get("door_max_open_sec", 60),
            variation_threshold_pct=10.0
        )
        door_det.set_perspective(cam_dict.get("perspective", "frontal"))

        obj_det = ObjectDetector(camera_id=cid)
        obj_det.set_person_enabled(bool(cam_dict.get("detect_person", 1)))
        obj_det.set_vehicle_enabled(bool(cam_dict.get("detect_vehicle", 1)))
        obj_det.set_sensitivities(cam_dict.get("person_sensitivity", 80), cam_dict.get("vehicle_sensitivity", 75))

        self.streams[cid] = stream
        self.door_detectors[cid] = door_det
        self.object_detectors[cid] = obj_det

        if cid == self.active_camera_id:
            stream.start()

    def process_camera_frame(self, camera_id: str) -> Dict[str, Any]:
        """Procesa el fotograma de cualquier cámara (para modo individual o cuadrícula multi-cámara)."""
        stream = self.streams.get(camera_id)
        door_det = self.door_detectors.get(camera_id)
        obj_det = self.object_detectors.get(camera_id)

        if not stream or not door_det or not obj_det:
            return {"frame": None, "state": "NO_CAMERA"}

        ret, frame, stream_state = stream.read_frame()

        # Detección de pérdida de señal
        lost_attr = f"_sig_lost_{camera_id}"
        if stream_state == CameraStream.STATE_SIGNAL_LOST:
            if not getattr(self, lost_attr, False):
                setattr(self, lost_attr, True)
                if self.on_signal_lost_callback:
                    self.on_signal_lost_callback(camera_id)
        else:
            setattr(self, lost_attr, False)

        if not ret or frame is None:
            blank = np.full((360, 640, 3), 15, dtype=np.uint8)
            cv2.putText(blank, f"SIN SENAL: {camera_id}", (180, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            cv2.putText(blank, "Intentando reconexion automatica...", (160, 215), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (160, 160, 160), 1)
            return {
                "frame": blank,
                "door_result": {"state": "SIN_SENAL", "elapsed_seconds": 0.0, "variation_pct": 0.0},
                "obj_result": {"persons": [], "vehicles": []},
                "stream_state": stream_state,
                "fps": 0.0
            }

        # 1. Procesar Estado de Puerta
        door_result = door_det.process_frame(frame)

        # Disparar alertas de puerta
        if door_result["is_alarm"] and not door_det.alarm_triggered_reported:
            door_det.alarm_triggered_reported = True
            if self.on_door_alarm_callback:
                self.on_door_alarm_callback(door_result)

        if not door_result["is_alarm"]:
            door_det.alarm_triggered_reported = False

        if door_result.get("just_closed"):
            if self.on_door_closed_callback:
                self.on_door_closed_callback(door_result)

        # 2. Procesar Personas y Vehículos de forma independiente
        obj_result = obj_det.detect(frame, stream_state)

        if obj_result.get("trigger_person_alert") and self.on_person_alert_callback:
            self.on_person_alert_callback(obj_result["person_alert_data"])

        if obj_result.get("trigger_vehicle_alert") and self.on_vehicle_alert_callback:
            self.on_vehicle_alert_callback(obj_result["vehicle_alert_data"])

        # 3. Superponer elementos visuales en el fotograma renderizado
        annotated = frame.copy()
        self._draw_overlays(annotated, door_result, obj_result, stream.fps)

        return {
            "frame": annotated,
            "door_result": door_result,
            "obj_result": obj_result,
            "stream_state": stream_state,
            "fps": stream.fps
        }

    def process_active_frame(self) -> Dict[str, Any]:
        """Captura y procesa el fotograma de la cámara activa actual."""
        return self.process_camera_frame(self.active_camera_id)

    def save_snapshot(self, camera_id: str, event_type: str = "ALERTA", frame: Optional[np.ndarray] = None) -> Optional[str]:
        """Captura y guarda una instantánea JPG de alta resolución con sello de tiempo y metadatos forenses."""
        try:
            from vigiwin.core.config import get_snapshots_dir
            sdir = get_snapshots_dir()

            if frame is None:
                stream = self.streams.get(camera_id)
                if stream:
                    _, frame, _ = stream.read_frame()

            if frame is None:
                # Generar fotograma de reserva con indicación forense
                frame = np.full((360, 640, 3), 18, dtype=np.uint8)
                cv2.putText(frame, f"VIGI-WIN PRO - CAPTURA FORENSE", (30, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 160), 2)
                cv2.putText(frame, f"CANAL: {camera_id} | EVENTO: {event_type}", (30, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (220, 220, 220), 1)

            snap = frame.copy()
            h, w = snap.shape[:2]

            # Estampar franja inferior forense
            bar_height = 28
            cv2.rectangle(snap, (0, h - bar_height), (w, h), (15, 23, 42), -1)
            ts_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            label = f"VIGI-WIN PRO | CAM: {camera_id} | EVENTO: {event_type} | {ts_str}"
            cv2.putText(snap, label, (12, h - 9), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (16, 185, 129), 1, cv2.LINE_AA)

            safe_type = "".join(c for c in event_type if c.isalnum() or c in ("_", "-"))
            now_slug = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]
            filename = f"snap_{camera_id}_{now_slug}_{safe_type}.jpg"
            filepath = sdir / filename
            cv2.imwrite(str(filepath), snap, [cv2.IMWRITE_JPEG_QUALITY, 92])
            return str(filepath)
        except Exception as e:
            print(f"Error al guardar snapshot forense: {e}")
            return None

    def _draw_overlays(self, frame: np.ndarray, door_result: Dict[str, Any], obj_result: Dict[str, Any], fps: float):
        h, w = frame.shape[:2]

        # Marco ROI de la Puerta
        if self.show_roi:
            roi = door_result.get("roi", {})
            rx, ry, rw, rh = roi.get("x", 250), roi.get("y", 80), roi.get("width", 140), roi.get("height", 200)
            
            # Color del marco de puerta según estado
            state = door_result.get("state", "CERRADO")
            if state == DoorDetector.STATE_ALARM:
                door_color = (0, 0, 255) # Rojo
                status_txt = f"PUERTA: ALARMA CRITICA ({door_result.get('elapsed_seconds')}s)"
            elif state == DoorDetector.STATE_OPEN:
                door_color = (0, 165, 255) # Naranja/Ámbar
                status_txt = f"PUERTA: ABIERTA [{door_result.get('variation_pct')}%] ({door_result.get('elapsed_seconds')}s)"
            elif state == DoorDetector.STATE_UNCERTAIN:
                door_color = (255, 255, 0) # Amarillo
                status_txt = "PUERTA: INCERTIDUMBRE"
            else:
                door_color = (0, 255, 120) # Verde esmeralda
                status_txt = f"PUERTA: CERRADA [{door_result.get('variation_pct')}%]"

            cv2.rectangle(frame, (rx, ry), (rx + rw, ry + rh), door_color, 2)
            cv2.putText(frame, status_txt, (rx, max(20, ry - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, door_color, 1, cv2.LINE_AA)

        # Bounding Boxes de Personas (Celeste #38bdf8 -> BGR 248, 189, 56)
        for p in obj_result.get("persons", []):
            bx, by, bw, bh = p["box"]
            conf = int(p["confidence"] * 100)
            cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (248, 189, 56), 2)
            cv2.putText(frame, f"Persona [{conf}%]", (bx, max(15, by - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (248, 189, 56), 1, cv2.LINE_AA)

        # Bounding Boxes de Vehículos (Ámbar #f59e0b -> BGR 11, 158, 245)
        for v in obj_result.get("vehicles", []):
            bx, by, bw, bh = v["box"]
            conf = int(v["confidence"] * 100)
            cat = v.get("category", "Vehículo")
            cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (11, 158, 245), 2)
            cv2.putText(frame, f"{cat} [{conf}%]", (bx, max(15, by - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (11, 158, 245), 1, cv2.LINE_AA)

        # Marco global ROI punteado
        if self.show_roi:
            cv2.rectangle(frame, (30, 25), (w - 30, h - 25), (70, 120, 70), 1)
            cv2.putText(frame, "ROI ACTIVO", (35, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (100, 180, 100), 1)

DoorDetector.alarm_triggered_reported = False
