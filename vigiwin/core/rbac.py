"""
VIGI-WIN PRO - Control de Acceso Basado en Roles (RBAC)
Gestión de sesiones, autenticación local, administración de usuarios y matriz de permisos.
"""
import copy
import hashlib
from typing import Optional, Dict, List, Tuple, Callable, Any

class RBACManager:
    PERMISSIONS = {
        "Administrador": [
            "view_live", "acknowledge_alert", "view_logs", "export_csv",
            "configure_cameras", "configure_detection", "configure_alerts",
            "manage_users", "manage_backups", "build_installer", "company_branding"
        ],
        "Operador": [
            "view_live", "acknowledge_alert", "view_logs", "export_csv"
        ],
        "Operador de Seguridad": [
            "view_live", "acknowledge_alert", "view_logs", "export_csv"
        ],
        "Auditor": [
            "view_logs", "export_csv"
        ]
    }

    # Definición amigable de cada permiso para interfaces y matrices
    PERMISSION_DEFINITIONS = {
        "view_live": {
            "label": "Monitoreo en Directo",
            "desc": "Visualizar cámaras y transmisiones RTSP/USB en vivo",
            "icon": "📹"
        },
        "acknowledge_alert": {
            "label": "Acuse de Alertas",
            "desc": "Confirmar, silenciar y atender alertas de seguridad",
            "icon": "🔔"
        },
        "view_logs": {
            "label": "Historial y Logs",
            "desc": "Consultar bitácora de eventos y auditoría del sistema",
            "icon": "📋"
        },
        "export_csv": {
            "label": "Exportación de Reportes",
            "desc": "Exportar eventos a archivos CSV / Excel",
            "icon": "📊"
        },
        "configure_cameras": {
            "label": "Configuración de Cámaras",
            "desc": "Añadir dispositivos DVR/NVR, RTSP, USB y calibrar ROI",
            "icon": "📷"
        },
        "configure_detection": {
            "label": "Parámetros de Detección",
            "desc": "Modificar umbrales IA de puertas, personas y vehículos",
            "icon": "🧠"
        },
        "configure_alerts": {
            "label": "Configuración de Alertas",
            "desc": "Ajustar audio de sirena, retardo de puerta y persistencia",
            "icon": "⚙️"
        },
        "company_branding": {
            "label": "Identidad y Empresa",
            "desc": "Modificar nombre institucional de la empresa y logotipo",
            "icon": "🏢"
        },
        "manage_users": {
            "label": "Gestión de Usuarios RBAC",
            "desc": "Crear, editar, activar, cambiar claves y roles de usuarios",
            "icon": "👥"
        },
        "manage_backups": {
            "label": "Copias de Seguridad",
            "desc": "Generar y restaurar backups JSON con verificación SHA-256",
            "icon": "💾"
        },
        "build_installer": {
            "label": "Compilador & Suite Tests",
            "desc": "Acceso a descarga de paquete .EXE y ejecución de tests 24P",
            "icon": "💻"
        }
    }

    ROLES_LIST = ["Administrador", "Operador", "Operador de Seguridad", "Auditor"]

    def __init__(self, db_manager):
        self.db = db_manager
        self.custom_permissions = copy.deepcopy(self.PERMISSIONS)
        self.current_user: Optional[Dict[str, Any]] = {
            "username": "admin",
            "role": "Administrador",
            "cargo": "Administrador del Sistema",
            "is_active": 1
        }
        self.on_user_changed: Optional[Callable[[Dict[str, Any]], None]] = None

    @staticmethod
    def hash_password(password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    def _notify_user_changed(self):
        if self.on_user_changed and callable(self.on_user_changed):
            try:
                self.on_user_changed(self.current_user or {})
            except Exception:
                pass

    def login(self, username: str, password: str) -> bool:
        pw_hash = self.hash_password(password)
        user = self.db.get_user(username)
        if user and user.get("password_hash") == pw_hash:
            if user.get("is_active", 1) != 1:
                return False
            self.current_user = {
                "username": user["username"],
                "role": user["role"],
                "cargo": user.get("cargo", "Operador"),
                "is_active": user.get("is_active", 1)
            }
            self.db.log_audit(username, "Inicio de Sesión", f"Rol: {user['role']} | Cargo: {user.get('cargo')}")
            self._notify_user_changed()
            return True
        return False

    def logout(self):
        if self.current_user:
            self.db.log_audit(self.current_user["username"], "Cierre de Sesión", "")
        self.current_user = None
        self._notify_user_changed()

    def switch_user(self, username: str) -> bool:
        """Conmutación rápida de sesión entre usuarios registrados."""
        user = self.db.get_user(username)
        if user:
            if user.get("is_active", 1) != 1:
                return False
            self.current_user = {
                "username": user["username"],
                "role": user["role"],
                "cargo": user.get("cargo", "Operador"),
                "is_active": user.get("is_active", 1)
            }
            self.db.log_audit(
                username,
                "Conmutación Rápida de Sesión",
                f"Cambiado a rol {user['role']} ({user.get('cargo')})"
            )
            self._notify_user_changed()
            return True
        return False

    def has_permission(self, permission: str) -> bool:
        if not self.current_user:
            return False
        role = self.current_user.get("role", "")
        return permission in self.custom_permissions.get(role, self.PERMISSIONS.get(role, []))

    def get_current_role(self) -> str:
        if self.current_user:
            return self.current_user.get("role", "Invitado")
        return "Invitado"

    def get_current_username(self) -> str:
        if self.current_user:
            return self.current_user.get("username", "Desconocido")
        return "Desconocido"

    def get_current_cargo(self) -> str:
        if self.current_user:
            return self.current_user.get("cargo", "Operador")
        return "Operador"

    # --- Gestión de Permisos Dinámicos (Matriz) ---
    def get_permissions(self, role: str) -> List[str]:
        return list(self.custom_permissions.get(role, []))

    def set_permission(self, role: str, permission: str, enabled: bool):
        target_roles = [role]
        if role in ("Operador", "Operador de Seguridad"):
            target_roles = ["Operador", "Operador de Seguridad"]

        for r in target_roles:
            if r not in self.custom_permissions:
                self.custom_permissions[r] = list(self.PERMISSIONS.get(r, []))
            perms = self.custom_permissions[r]
            if enabled and permission not in perms:
                perms.append(permission)
            elif not enabled and permission in perms:
                perms.remove(permission)

        self._notify_user_changed()

    def reset_permissions_to_default(self):
        self.custom_permissions = copy.deepcopy(self.PERMISSIONS)
        self._notify_user_changed()

    # --- Operaciones CRUD de Usuarios ---
    def get_users(self) -> List[Dict[str, Any]]:
        return self.db.get_users()

    def create_user(self, username: str, password: str, role: str, cargo: str = "Operador de Monitoreo", is_active: int = 1) -> Tuple[bool, str]:
        username = username.strip()
        cargo = cargo.strip() or "Operador de Monitoreo"
        if not username:
            return False, "El nombre de usuario no puede estar vacío."
        if len(password) < 4:
            return False, "La contraseña debe tener al menos 4 caracteres."
        if role not in self.ROLES_LIST:
            return False, f"Rol no válido: {role}."

        existing = self.db.get_user(username)
        if existing:
            return False, f"El usuario '{username}' ya existe en el sistema."

        pw_hash = self.hash_password(password)
        success = self.db.create_user(username, pw_hash, role, cargo, is_active)
        if success:
            actor = self.get_current_username()
            self.db.log_audit(actor, "Crear Usuario", f"Usuario creado: {username} ({role}) - Cargo: {cargo} - Activo: {is_active}")
            return True, f"Usuario '{username}' creado exitosamente con rol {role}."
        return False, "Error al registrar el usuario en la base de datos."

    def update_user(self, username: str, role: Optional[str] = None, cargo: Optional[str] = None, is_active: Optional[int] = None, new_password: Optional[str] = None) -> Tuple[bool, str]:
        user = self.db.get_user(username)
        if not user:
            return False, f"El usuario '{username}' no existe."

        # Salvaguarda: No permitir desactivar la sesión activa
        if self.current_user and self.current_user.get("username") == username and is_active == 0:
            return False, "No puedes desactivar el usuario de la sesión actualmente activa."

        # Salvaguarda: Si es Administrador y se degrada o desactiva, verificar que quede al menos un Administrador activo
        is_current_admin = (user.get("role") == "Administrador" and user.get("is_active", 1) == 1)
        will_be_admin = (role == "Administrador" if role is not None else user.get("role") == "Administrador") and (is_active == 1 if is_active is not None else user.get("is_active", 1) == 1)

        if is_current_admin and not will_be_admin:
            active_admins = [u for u in self.get_users() if u.get("role") == "Administrador" and u.get("is_active", 1) == 1]
            if len(active_admins) <= 1:
                return False, "No se puede degradar ni desactivar al único Administrador activo del sistema."

        # Actualizar contraseña si se proporcionó una nueva
        if new_password:
            if len(new_password) < 4:
                return False, "La nueva contraseña debe tener al menos 4 caracteres."
            pw_hash = self.hash_password(new_password)
            self.db.update_user_password(username, pw_hash)

        success = self.db.update_user(username, role=role, cargo=cargo, is_active=is_active)
        if success:
            actor = self.get_current_username()
            self.db.log_audit(actor, "Modificar Usuario", f"Usuario modificado: {username} (Rol: {role}, Cargo: {cargo}, Activo: {is_active})")
            # Si el usuario editado es el actual, refrescar su sesión
            if self.current_user and self.current_user.get("username") == username:
                if role is not None: self.current_user["role"] = role
                if cargo is not None: self.current_user["cargo"] = cargo
                if is_active is not None: self.current_user["is_active"] = is_active
                self._notify_user_changed()
            return True, f"Usuario '{username}' actualizado correctamente."
        return False, f"No se pudo actualizar el usuario '{username}'."

    def change_password(self, username: str, new_password: str) -> Tuple[bool, str]:
        if len(new_password) < 4:
            return False, "La nueva contraseña debe tener al menos 4 caracteres."
        pw_hash = self.hash_password(new_password)
        success = self.db.update_user_password(username, pw_hash)
        if success:
            actor = self.get_current_username()
            self.db.log_audit(actor, "Cambio de Contraseña", f"Contraseña actualizada para: {username}")
            return True, f"Contraseña de '{username}' actualizada correctamente."
        return False, f"No se pudo actualizar la contraseña de '{username}'."

    def change_role(self, username: str, new_role: str) -> Tuple[bool, str]:
        return self.update_user(username, role=new_role)

    def delete_user(self, username: str) -> Tuple[bool, str]:
        if self.current_user and self.current_user.get("username") == username:
            return False, "No puedes eliminar al usuario de la sesión actualmente activa."

        user = self.db.get_user(username)
        if not user:
            return False, f"El usuario '{username}' no fue encontrado."

        if user["role"] == "Administrador":
            admins = [u for u in self.get_users() if u["role"] == "Administrador" and u.get("is_active", 1) == 1]
            if len(admins) <= 1:
                return False, "No se puede eliminar el único Administrador activo del sistema."

        success = self.db.delete_user(username)
        if success:
            actor = self.get_current_username()
            self.db.log_audit(actor, "Eliminar Usuario", f"Usuario eliminado: {username}")
            return True, f"Usuario '{username}' eliminado del sistema."
        return False, f"Error al eliminar al usuario '{username}'."

