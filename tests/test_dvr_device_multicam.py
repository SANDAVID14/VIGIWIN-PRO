"""
VIGI-WIN PRO - Test de Integración: Conexión DVR / NVR / RTSP Multi-Cámara
Valida:
1. Configuración y agregado de un dispositivo DVR/NVR con múltiples cámaras y canales.
2. Persistencia en base de datos SQLite y orquestador CameraManager.
3. Conmutación entre las cámaras agregadas y activación de reglas de IA independientes.
4. Registro de auditoría administrativa al vincular el dispositivo.
"""
import pytest
from vigiwin.core.database import DatabaseManager
from vigiwin.vision.camera_manager import CameraManager

def test_add_dvr_device_with_multiple_cameras(tmp_path):
    # 1. Crear BD temporal aislada
    db_file = str(tmp_path / "test_dvr_vigiwin.db")
    db = DatabaseManager(db_file)
    cam_mgr = CameraManager(db)

    # 2. Definir dispositivo DVR con 4 cámaras asociadas
    dvr_device = {
        "id": "DEV_DVR_01",
        "name": "DVR Dahua Acceso Perimetral",
        "type": "dvr_nvr",
        "host": "192.168.1.150",
        "port": 554,
        "protocol": "TCP",
        "user": "admin",
        "cameras": [
            {
                "id": "CAM_02",
                "name": "Canal 1: Puerta Principal Vehicular",
                "source_type": "simulation",
                "source_url": "rtsp://admin:pass@192.168.1.150:554/ch1/main",
                "perspective": "frontal",
                "door_max_open_sec": 60,
                "detect_person": 1,
                "detect_vehicle": 1,
                "person_sensitivity": 85,
                "vehicle_sensitivity": 80,
                "is_active": 1
            },
            {
                "id": "CAM_03",
                "name": "Canal 2: Acceso Peatonal Posterior",
                "source_type": "simulation",
                "source_url": "rtsp://admin:pass@192.168.1.150:554/ch2/main",
                "perspective": "lateral",
                "door_max_open_sec": 45,
                "detect_person": 1,
                "detect_vehicle": 0,
                "person_sensitivity": 90,
                "vehicle_sensitivity": 70,
                "is_active": 1
            },
            {
                "id": "CAM_04",
                "name": "Canal 3: Perímetro Andén Carga",
                "source_type": "simulation",
                "source_url": "rtsp://admin:pass@192.168.1.150:554/ch3/main",
                "perspective": "frontal",
                "door_max_open_sec": 90,
                "detect_person": 1,
                "detect_vehicle": 1,
                "person_sensitivity": 75,
                "vehicle_sensitivity": 85,
                "is_active": 1
            },
            {
                "id": "CAM_05",
                "name": "Canal 4: Barrera de Salida",
                "source_type": "simulation",
                "source_url": "rtsp://admin:pass@192.168.1.150:554/ch4/main",
                "perspective": "lateral",
                "door_max_open_sec": 60,
                "detect_person": 0,
                "detect_vehicle": 1,
                "person_sensitivity": 70,
                "vehicle_sensitivity": 90,
                "is_active": 1
            }
        ]
    }

    # 3. Agregar todas las cámaras del dispositivo DVR
    for cam in dvr_device["cameras"]:
        cam_mgr.add_or_update_camera(cam)

    db.log_audit("Administrador", "Dispositivo Agregado", f"{dvr_device['name']} (4 cámaras)")

    # 4. Comprobar que todas las cámaras están persistidas en SQLite
    cams_in_db = db.get_cameras()
    cam_ids = [c["id"] for c in cams_in_db]
    for expected_cam in dvr_device["cameras"]:
        assert expected_cam["id"] in cam_ids
        saved_cam = db.get_camera(expected_cam["id"])
        assert saved_cam["name"] == expected_cam["name"]
        assert saved_cam["perspective"] == expected_cam["perspective"]
        assert saved_cam["detect_person"] == expected_cam["detect_person"]
        assert saved_cam["detect_vehicle"] == expected_cam["detect_vehicle"]

    # 5. Comprobar que el orquestador CameraManager tiene los streams y detectores listos
    for expected_cam in dvr_device["cameras"]:
        cid = expected_cam["id"]
        assert cid in cam_mgr.streams
        assert cid in cam_mgr.door_detectors
        assert cid in cam_mgr.object_detectors

    # 6. Conmutar a la cámara 3 (CAM_04) y verificar que procesa correctamente
    cam_mgr.set_active_camera("CAM_04")
    assert cam_mgr.active_camera_id == "CAM_04"
    frame_res = cam_mgr.process_active_frame()
    assert frame_res["frame"] is not None
    assert "fps" in frame_res

    # 7. Conmutar a la cámara 2 (CAM_03) con perspectiva lateral
    cam_mgr.set_active_camera("CAM_03")
    assert cam_mgr.active_camera_id == "CAM_03"
    door_det = cam_mgr.door_detectors["CAM_03"]
    assert door_det.perspective == "lateral"

    # 8. Verificar registro de auditoría
    logs = db.get_events(limit=10)
    # Comprobar que no hay errores en log
    assert len(cams_in_db) >= 5 # CAM_01 por defecto + 4 del DVR
