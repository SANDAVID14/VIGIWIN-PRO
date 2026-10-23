"""
VIGI-WIN PRO - Gestor de Copias de Seguridad y Restauración
Copia íntegra de base de datos y configuraciones con validación SHA-256.
"""
import os
import json
import shutil
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Tuple, Dict, Any

from vigiwin.core.config import get_backups_dir, get_db_path

class BackupManager:
    def __init__(self, db_manager):
        self.db = db_manager
        self.backups_dir = get_backups_dir()

    def create_json_backup(self, target_filepath: str) -> Tuple[bool, str]:
        """Crea un volcado completo de settings, cámaras y eventos en formato JSON con checksum."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Obtener settings
                cursor.execute("SELECT key, value FROM settings")
                settings = {row["key"]: row["value"] for row in cursor.fetchall()}
                
                # Obtener cámaras
                cursor.execute("SELECT * FROM cameras")
                cameras = [dict(row) for row in cursor.fetchall()]
                
                # Obtener eventos
                cursor.execute("SELECT * FROM events ORDER BY id ASC")
                events = [dict(row) for row in cursor.fetchall()]

                # Obtener usuarios
                cursor.execute("SELECT username, password_hash, role, created_at FROM users")
                users = [dict(row) for row in cursor.fetchall()]

            backup_data = {
                "version": "1.0",
                "software": "VIGI-WIN PRO",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "settings": settings,
                "cameras": cameras,
                "events": events,
                "users": users
            }

            content_str = json.dumps(backup_data, indent=2, ensure_ascii=False)
            checksum = hashlib.sha256(content_str.encode('utf-8')).hexdigest()
            backup_data["checksum_sha256"] = checksum

            with open(target_filepath, "w", encoding="utf-8") as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)

            self.db.set_setting("last_backup_date", backup_data["created_at"])
            self.db.log_audit("Sistema", "Backup Creado", f"Archivo: {target_filepath}")
            return True, f"Copia de seguridad guardada con éxito en {target_filepath}"
        except Exception as e:
            return False, f"Error al generar copia de seguridad: {e}"

    def create_sqlite_backup(self, target_filepath: str) -> Tuple[bool, str]:
        """Crea una copia física binaria de la base de datos SQLite."""
        try:
            src = get_db_path()
            shutil.copy2(src, target_filepath)
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.db.set_setting("last_backup_date", now_str)
            self.db.log_audit("Sistema", "Backup DB SQLite", f"Destino: {target_filepath}")
            return True, f"Base de datos SQLite respaldada correctamente en {target_filepath}"
        except Exception as e:
            return False, f"Error al copiar base de datos: {e}"

    def validate_backup_file(self, filepath: str) -> Tuple[bool, str, Dict[str, Any]]:
        """Verifica la integridad de un archivo de backup JSON verificando su hash SHA-256."""
        if not os.path.exists(filepath):
            return False, "El archivo no existe", {}

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            if "checksum_sha256" not in data or "version" not in data:
                return False, "Estructura de copia de seguridad no válida o dañada", {}

            expected_checksum = data.pop("checksum_sha256")
            content_str = json.dumps(data, indent=2, ensure_ascii=False)
            calculated_checksum = hashlib.sha256(content_str.encode('utf-8')).hexdigest()

            if expected_checksum != calculated_checksum:
                return False, "Error de integridad: el archivo ha sido modificado o está corrupto", {}

            return True, f"Copia íntegra válida (Versión {data.get('version')}, Creada: {data.get('created_at')})", data
        except Exception as e:
            return False, f"Error al validar el archivo: {e}", {}

    def restore_from_json(self, filepath: str) -> Tuple[bool, str]:
        """Restaura todos los datos y configuraciones desde un archivo JSON validado."""
        is_valid, msg, data = self.validate_backup_file(filepath)
        if not is_valid:
            return False, msg

        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Restaurar settings
                for k, v in data.get("settings", {}).items():
                    cursor.execute("""
                        INSERT INTO settings (key, value) VALUES (?, ?)
                        ON CONFLICT(key) DO UPDATE SET value = excluded.value
                    """, (k, v))

                # Restaurar cámaras
                for cam in data.get("cameras", []):
                    cursor.execute("""
                        INSERT INTO cameras (id, name, source_type, source_url, perspective, door_roi_json, door_max_open_sec, detect_person, detect_vehicle, person_sensitivity, vehicle_sensitivity, is_active)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(id) DO UPDATE SET
                            name = excluded.name,
                            source_type = excluded.source_type,
                            source_url = excluded.source_url,
                            perspective = excluded.perspective,
                            door_roi_json = excluded.door_roi_json,
                            door_max_open_sec = excluded.door_max_open_sec,
                            detect_person = excluded.detect_person,
                            detect_vehicle = excluded.detect_vehicle,
                            person_sensitivity = excluded.person_sensitivity,
                            vehicle_sensitivity = excluded.vehicle_sensitivity,
                            is_active = excluded.is_active
                    """, (
                        cam["id"], cam["name"], cam["source_type"], cam["source_url"],
                        cam.get("perspective", "frontal"), cam.get("door_roi_json"),
                        cam.get("door_max_open_sec", 60), cam.get("detect_person", 1),
                        cam.get("detect_vehicle", 1), cam.get("person_sensitivity", 80),
                        cam.get("vehicle_sensitivity", 75), cam.get("is_active", 1)
                    ))

                # Restaurar eventos si se desea conservar historial
                for ev in data.get("events", []):
                    cursor.execute("""
                        INSERT OR IGNORE INTO events (id, timestamp, camera, event_type, message, priority, confirmed, confirmed_at, confirmed_by, details_json)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        ev["id"], ev["timestamp"], ev["camera"], ev["event_type"],
                        ev["message"], ev["priority"], ev.get("confirmed", 0),
                        ev.get("confirmed_at"), ev.get("confirmed_by"), ev.get("details_json")
                    ))

                conn.commit()

            self.db.log_audit("Sistema", "Restauración Completada", f"Desde {filepath}")
            return True, "Configuración y datos restaurados exitosamente."
        except Exception as e:
            return False, f"Fallo al restaurar: {e}"

    def get_last_backup_date(self) -> str:
        date = self.db.get_setting("last_backup_date", "Nunca")
        return str(date)
