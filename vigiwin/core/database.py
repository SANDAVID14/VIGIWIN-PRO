"""
VIGI-WIN PRO - Motor de Base de Datos SQLite
Persistencia local, segura, sin dependencias externas ni servicios de pago.
"""
import sqlite3
import json
import csv
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from vigiwin.core.config import get_db_path, DEFAULT_SETTINGS

class DatabaseManager:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or get_db_path()
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Inicializa las tablas del esquema si no existen."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Tabla de Eventos y Alarmas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    camera TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    confirmed INTEGER DEFAULT 0,
                    confirmed_at TEXT,
                    confirmed_by TEXT,
                    details_json TEXT,
                    snapshot_path TEXT
                )
            """)

            # Migración automática si la tabla events existía con un esquema anterior
            cursor.execute("PRAGMA table_info(events)")
            ev_cols = {row[1] for row in cursor.fetchall()}
            if "details_json" not in ev_cols:
                cursor.execute("ALTER TABLE events ADD COLUMN details_json TEXT")
            if "confirmed_at" not in ev_cols:
                cursor.execute("ALTER TABLE events ADD COLUMN confirmed_at TEXT")
            if "confirmed_by" not in ev_cols:
                cursor.execute("ALTER TABLE events ADD COLUMN confirmed_by TEXT")
            if "snapshot_path" not in ev_cols:
                cursor.execute("ALTER TABLE events ADD COLUMN snapshot_path TEXT")

            # 2. Tabla de Cámaras y Calibración
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cameras (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    perspective TEXT DEFAULT 'frontal',
                    door_roi_json TEXT,
                    door_max_open_sec INTEGER DEFAULT 60,
                    detect_person INTEGER DEFAULT 1,
                    detect_vehicle INTEGER DEFAULT 1,
                    person_sensitivity INTEGER DEFAULT 80,
                    vehicle_sensitivity INTEGER DEFAULT 75,
                    is_active INTEGER DEFAULT 1
                )
            """)

            # Migración automática si la tabla cameras existía con un esquema anterior
            cursor.execute("PRAGMA table_info(cameras)")
            cam_cols = {row[1] for row in cursor.fetchall()}
            if "source_type" not in cam_cols:
                cursor.execute("DROP TABLE cameras")
                cursor.execute("""
                    CREATE TABLE cameras (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        source_type TEXT NOT NULL,
                        source_url TEXT NOT NULL,
                        perspective TEXT DEFAULT 'frontal',
                        door_roi_json TEXT,
                        door_max_open_sec INTEGER DEFAULT 60,
                        detect_person INTEGER DEFAULT 1,
                        detect_vehicle INTEGER DEFAULT 1,
                        person_sensitivity INTEGER DEFAULT 80,
                        vehicle_sensitivity INTEGER DEFAULT 75,
                        is_active INTEGER DEFAULT 1
                    )
                """)

            # 3. Tabla de Configuraciones del Sistema
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

            # 4. Tabla de Usuarios y Roles (RBAC)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL,
                    cargo TEXT DEFAULT 'Operador de Monitoreo',
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL
                )
            """)

            # Migración automática si la tabla users existía con esquema anterior
            cursor.execute("PRAGMA table_info(users)")
            user_cols = {row[1] for row in cursor.fetchall()}
            if "cargo" not in user_cols:
                cursor.execute("ALTER TABLE users ADD COLUMN cargo TEXT DEFAULT 'Operador de Monitoreo'")
            if "is_active" not in user_cols:
                cursor.execute("ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1")

            # 5. Registro de Auditoría Administrativa
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    username TEXT NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT
                )
            """)

            conn.commit()

        # Poblar configuración y usuarios iniciales si la BD es nueva
        self._seed_initial_data()

    def _seed_initial_data(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Poblar settings por defecto si no existen
            for k, v in DEFAULT_SETTINGS.items():
                cursor.execute(
                    "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                    (k, json.dumps(v))
                )

            # Poblar cámara 01 por defecto
            cursor.execute("""
                INSERT OR IGNORE INTO cameras 
                (id, name, source_type, source_url, perspective, door_roi_json, door_max_open_sec, detect_person, detect_vehicle, person_sensitivity, vehicle_sensitivity, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "CAM_01",
                "Entrada Principal / Vehicular",
                "webcam",
                "0",
                "frontal",
                json.dumps({"x": 240, "y": 80, "width": 160, "height": 220}),
                60,
                1,
                1,
                80,
                75,
                1
            ))

            # Poblar usuarios RBAC iniciales (hash SHA-256 seguro)
            def hash_pw(pw: str) -> str:
                return hashlib.sha256(pw.encode()).hexdigest()

            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            initial_users = [
                ("admin", hash_pw("admin123"), "Administrador", "Administrador del Sistema", 1, now_str),
                ("operador", hash_pw("operador123"), "Operador de Seguridad", "Operador de Seguridad y Monitoreo", 1, now_str),
                ("auditor", hash_pw("auditor123"), "Auditor", "Auditor de Cumplimiento", 1, now_str)
            ]
            for user, pw_hash, role, cargo, is_active, created in initial_users:
                cursor.execute(
                    "INSERT OR IGNORE INTO users (username, password_hash, role, cargo, is_active, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (user, pw_hash, role, cargo, is_active, created)
                )

            conn.commit()

    # --- Operaciones de Eventos ---
    def log_event(self, camera: str, event_type: str, message: str, priority: str = "Media", details: Optional[Dict] = None, snapshot_path: Optional[str] = None) -> int:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        details_dict = dict(details or {})
        if snapshot_path:
            details_dict["snapshot_path"] = snapshot_path
        details_str = json.dumps(details_dict)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO events (timestamp, camera, event_type, message, priority, details_json, snapshot_path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (timestamp, camera, event_type, message, priority, details_str, snapshot_path))
            conn.commit()
            return cursor.lastrowid

    def confirm_event(self, event_id: int, username: str = "Operador") -> bool:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE events 
                SET confirmed = 1, confirmed_at = ?, confirmed_by = ?
                WHERE id = ?
            """, (now_str, username, event_id))
            conn.commit()
            return cursor.rowcount > 0

    def get_events(self, limit: int = 100, category: str = "ALL", search: str = "", camera: str = "ALL") -> List[Dict[str, Any]]:
        query = "SELECT * FROM events WHERE 1=1"
        params = []

        if category != "ALL":
            query += " AND event_type LIKE ?"
            params.append(f"%{category}%")

        if camera != "ALL":
            query += " AND camera = ?"
            params.append(camera)

        if search:
            query += " AND (message LIKE ? OR event_type LIKE ? OR camera LIKE ?)"
            s_param = f"%{search}%"
            params.extend([s_param, s_param, s_param])

        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def export_events_csv(self, file_path: str) -> int:
        events = self.get_events(limit=5000)
        with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Fecha/Hora", "Cámara", "Tipo de Evento", "Mensaje", "Prioridad", "Confirmado", "Confirmado En", "Confirmado Por", "Evidencia Snapshot"])
            for e in events:
                writer.writerow([
                    e["id"], e["timestamp"], e["camera"], e["event_type"],
                    e["message"], e["priority"], "Sí" if e["confirmed"] else "No",
                    e["confirmed_at"] or "", e["confirmed_by"] or "",
                    e.get("snapshot_path") or ""
                ])
        return len(events)

    # --- Operaciones de Ajustes (Settings) ---
    def set_setting(self, key: str, value: Any):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """, (key, json.dumps(value)))
            conn.commit()

    def get_setting(self, key: str, default: Any = None) -> Any:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                try:
                    return json.loads(row["value"])
                except Exception:
                    return row["value"]
            return default

    def get_all_settings(self) -> Dict[str, Any]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM settings")
            rows = cursor.fetchall()
            result = {}
            for r in rows:
                try:
                    result[r["key"]] = json.loads(r["value"])
                except Exception:
                    result[r["key"]] = r["value"]
            return result


    # --- Operaciones de Cámaras ---
    def get_cameras(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM cameras WHERE is_active = 1 ORDER BY id ASC")
            rows = cursor.fetchall()
            result = []
            for r in rows:
                item = dict(r)
                if item["door_roi_json"]:
                    try:
                        item["door_roi"] = json.loads(item["door_roi_json"])
                    except Exception:
                        item["door_roi"] = None
                else:
                    item["door_roi"] = None
                result.append(item)
            return result

    def get_camera(self, camera_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM cameras WHERE id = ?", (camera_id,))
            row = cursor.fetchone()
            if row:
                item = dict(row)
                if item["door_roi_json"]:
                    try:
                        item["door_roi"] = json.loads(item["door_roi_json"])
                    except Exception:
                        item["door_roi"] = None
                return item
            return None

    def save_camera(self, camera_data: Dict[str, Any]):
        door_roi_json = json.dumps(camera_data.get("door_roi")) if camera_data.get("door_roi") else None
        with self.get_connection() as conn:
            cursor = conn.cursor()
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
                camera_data["id"],
                camera_data.get("name", "Cámara"),
                camera_data.get("source_type", "webcam"),
                camera_data.get("source_url", "0"),
                camera_data.get("perspective", "frontal"),
                door_roi_json,
                camera_data.get("door_max_open_sec", 60),
                1 if camera_data.get("detect_person", True) else 0,
                1 if camera_data.get("detect_vehicle", True) else 0,
                camera_data.get("person_sensitivity", 80),
                camera_data.get("vehicle_sensitivity", 75),
                1 if camera_data.get("is_active", True) else 0
            ))
            conn.commit()

    def update_camera_calibration(self, camera_id: str, perspective: str, door_roi: Dict[str, Any]):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE cameras 
                SET perspective = ?, door_roi_json = ?
                WHERE id = ?
            """, (perspective, json.dumps(door_roi), camera_id))
            conn.commit()

    # --- Operaciones de Auditoría ---
    def log_audit(self, username: str, action: str, details: str = ""):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO audit_log (timestamp, username, action, details)
                VALUES (?, ?, ?, ?)
            """, (now_str, username, action, details))
            conn.commit()

    def get_audit_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]

    # --- Operaciones de Usuarios (RBAC) ---
    def get_users(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT username, role, cargo, is_active, created_at FROM users ORDER BY created_at ASC")
            return [dict(row) for row in cursor.fetchall()]

    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT username, password_hash, role, cargo, is_active, created_at FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def create_user(self, username: str, password_hash: str, role: str, cargo: str = "Operador de Monitoreo", is_active: int = 1) -> bool:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO users (username, password_hash, role, cargo, is_active, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (username, password_hash, role, cargo, is_active, now_str)
                )
                conn.commit()
                return True
            except Exception:
                return False

    def update_user(self, username: str, role: Optional[str] = None, cargo: Optional[str] = None, is_active: Optional[int] = None) -> bool:
        fields = []
        params = []
        if role is not None:
            fields.append("role = ?")
            params.append(role)
        if cargo is not None:
            fields.append("cargo = ?")
            params.append(cargo)
        if is_active is not None:
            fields.append("is_active = ?")
            params.append(int(is_active))
        if not fields:
            return False
        params.append(username)
        query = f"UPDATE users SET {', '.join(fields)} WHERE username = ?"
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount > 0

    def update_user_password(self, username: str, new_password_hash: str) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET password_hash = ? WHERE username = ?", (new_password_hash, username))
            conn.commit()
            return cursor.rowcount > 0

    def update_user_role(self, username: str, new_role: str) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET role = ? WHERE username = ?", (new_role, username))
            conn.commit()
            return cursor.rowcount > 0

    def delete_user(self, username: str) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE username = ?", (username,))
            conn.commit()
            return cursor.rowcount > 0

    def update_camera_detection(self, camera_id: str, detect_person: int, detect_vehicle: int, person_sens: int, vehicle_sens: int, max_open_sec: int) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE cameras 
                SET detect_person = ?, detect_vehicle = ?, person_sensitivity = ?, vehicle_sensitivity = ?, door_max_open_sec = ?
                WHERE id = ?
            """, (detect_person, detect_vehicle, person_sens, vehicle_sens, max_open_sec, camera_id))
            conn.commit()
            return cursor.rowcount > 0

