"""
VIGI-WIN PRO - Gestor de Configuración Centralizada
Almacena y gestiona valores por defecto y rutas del sistema.
"""
import os
import json
from pathlib import Path

# Directorio de usuario local protegido
def get_app_data_dir() -> Path:
    user_home = Path.home()
    app_dir = user_home / ".vigiwinpro"
    try:
        app_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        app_dir = Path(os.path.abspath(".")) / ".vigiwinpro_data"
        app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir

def get_db_path() -> str:
    return str(get_app_data_dir() / "vigiwin.db")

def get_backups_dir() -> Path:
    bdir = get_app_data_dir() / "backups"
    bdir.mkdir(parents=True, exist_ok=True)
    return bdir

def get_snapshots_dir() -> Path:
    sdir = get_app_data_dir() / "snapshots"
    sdir.mkdir(parents=True, exist_ok=True)
    return sdir


DEFAULT_SETTINGS = {
    # Puertas
    "door_max_open_seconds": 60,       # 60 segundos por defecto (1 minuto)
    "door_variation_threshold_pct": 10, # 10% de variación de posición
    "door_sound_alert": True,
    "door_priority": "Alta",
    
    # Personas
    "person_detection_enabled": True,
    "person_sensitivity": 80,          # 80% confianza
    "person_persistence_sec": 1.0,     # Persistencia mínima
    "person_cooldown_sec": 15.0,       # Antispam
    "person_sound_alert": True,
    "person_priority": "Media",

    # Vehículos
    "vehicle_detection_enabled": True,
    "vehicle_sensitivity": 75,         # 75% confianza
    "vehicle_persistence_sec": 1.0,
    "vehicle_cooldown_sec": 15.0,
    "vehicle_sound_alert": True,
    "vehicle_priority": "Media",

    # Alertas UI
    "alert_always_topmost": True,
    "alert_sound_enabled": True,
    "alert_volume": 100,
    "alert_duration_seconds": 15,
    "alert_theme": "dark_slate",

    # Cámaras por defecto
    "selected_camera_id": "CAM_01",

    # Identidad Corporativa y Marca
    "company_name": "VigiWin Pro - Sistema Inteligente de Vigilancia",
    "company_logo_path": ""
}
