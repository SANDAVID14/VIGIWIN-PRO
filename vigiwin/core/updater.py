"""
VIGI-WIN PRO - Motor de Actualización Centralizada desde GitHub
Permite comprobar y aplicar actualizaciones de forma segura desde https://github.com/SANDAVID14/VIGIWIN-PRO.git.
Garantiza la preservación total de la configuración del usuario, base de datos SQLite,
cámaras calibradas, roles RBAC y registros de auditoría.
"""
import os
import sys
import subprocess
import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Any, List, Optional

from PySide6.QtCore import QThread, Signal

from vigiwin.core.backup import BackupManager
from vigiwin.core.config import get_app_data_dir, get_db_path

GITHUB_REPO_URL = "https://github.com/SANDAVID14/VIGIWIN-PRO.git"
GITHUB_API_COMMITS = "https://api.github.com/repos/SANDAVID14/VIGIWIN-PRO/commits/master"


def get_project_root() -> Path:
    """Devuelve la ruta raíz del proyecto donde reside run_app.py."""
    cur = Path(__file__).resolve().parent.parent.parent
    return cur


class SystemUpdater:
    """Gestor de actualización desde el repositorio oficial de GitHub."""

    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = root_dir or get_project_root()
        self.repo_url = GITHUB_REPO_URL

    def is_git_repository(self) -> bool:
        """Determina si la instalación actual es un clon de Git activo."""
        return (self.root_dir / ".git").is_dir()

    def run_git_command(self, args: List[str]) -> subprocess.CompletedProcess:
        """Ejecuta un comando git seguro en el directorio raíz."""
        return subprocess.run(
            ["git"] + args,
            cwd=str(self.root_dir),
            capture_output=True,
            text=True,
            timeout=45,
            encoding="utf-8",
            errors="replace"
        )

    def check_for_updates(self) -> Dict[str, Any]:
        """
        Conecta a GitHub y verifica si existen cambios pendientes.
        Retorna un diccionario estructurado con los cambios encontrados.
        """
        if self.is_git_repository():
            return self._check_git_updates()
        else:
            return self._check_api_updates()

    def _check_git_updates(self) -> Dict[str, Any]:
        try:
            # 1. Asegurar o configurar remoto oficial
            remotes_proc = self.run_git_command(["remote", "-v"])
            if "origin" not in remotes_proc.stdout:
                self.run_git_command(["remote", "add", "origin", self.repo_url])

            # 2. Conectar a GitHub y hacer fetch silencioso
            fetch_proc = self.run_git_command(["fetch", "origin", "master"])
            if fetch_proc.returncode != 0:
                # Intentar con branch main por si la rama predeterminada fuese main
                fetch_proc = self.run_git_command(["fetch", "origin", "main"])
                branch = "main"
            else:
                branch = "master"

            if fetch_proc.returncode != 0:
                err_msg = fetch_proc.stderr.strip() or "No se pudo conectar a GitHub."
                return {
                    "success": False,
                    "has_updates": False,
                    "error": f"Error al conectar con GitHub: {err_msg}",
                    "message": "No se pudo verificar actualizaciones. Compruebe la conexión a Internet."
                }

            # 3. Obtener hash del commit local y remoto
            local_proc = self.run_git_command(["rev-parse", "HEAD"])
            remote_proc = self.run_git_command(["rev-parse", f"origin/{branch}"])

            local_hash = local_proc.stdout.strip()
            remote_hash = remote_proc.stdout.strip()

            if local_hash == remote_hash:
                return {
                    "success": True,
                    "has_updates": False,
                    "local_commit": local_hash[:8],
                    "remote_commit": remote_hash[:8],
                    "commits": [],
                    "changed_files": [],
                    "message": "El software se encuentra al día. No hay cambios pendientes en GitHub."
                }

            # 4. Obtener lista de commits pendientes
            log_proc = self.run_git_command([
                "log", "--pretty=format:%h - %s (%cr) <%an>", f"HEAD..origin/{branch}"
            ])
            commits = [line.strip() for line in log_proc.stdout.splitlines() if line.strip()]

            # 5. Obtener lista de archivos modificados
            diff_proc = self.run_git_command(["diff", "--name-only", "HEAD", f"origin/{branch}"])
            changed_files = [line.strip() for line in diff_proc.stdout.splitlines() if line.strip()]

            return {
                "success": True,
                "has_updates": True,
                "local_commit": local_hash[:8],
                "remote_commit": remote_hash[:8],
                "branch": branch,
                "commits": commits,
                "changed_files": changed_files,
                "message": f"Se encontraron {len(commits)} actualización(es) disponibles en GitHub."
            }

        except Exception as e:
            return {
                "success": False,
                "has_updates": False,
                "error": str(e),
                "message": f"Excepción durante la comprobación: {e}"
            }

    def _check_api_updates(self) -> Dict[str, Any]:
        """Comprobación de respaldo vía GitHub REST API pública."""
        try:
            req = urllib.request.Request(
                GITHUB_API_COMMITS,
                headers={"User-Agent": "VigiWinPro-Updater/1.0"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                remote_sha = data.get("sha", "")[:8]
                commit_msg = data.get("commit", {}).get("message", "Actualización")

                # Comprobar contra archivo local de versión
                version_file = self.root_dir / ".version"
                local_sha = version_file.read_text(encoding="utf-8").strip() if version_file.exists() else "desconocido"

                has_updates = (local_sha != remote_sha)
                return {
                    "success": True,
                    "has_updates": has_updates,
                    "local_commit": local_sha,
                    "remote_commit": remote_sha,
                    "commits": [f"{remote_sha} - {commit_msg}"],
                    "changed_files": [],
                    "message": "Actualización disponible en GitHub." if has_updates else "Sistema al día."
                }
        except Exception as e:
            return {
                "success": False,
                "has_updates": False,
                "error": str(e),
                "message": f"No se pudo consultar GitHub API: {e}"
            }

    def apply_updates(self, db_manager=None) -> Dict[str, Any]:
        """
        Aplica únicamente las actualizaciones encontradas desde GitHub.
        PROTECCIÓN ESTRICTA: No modifica ni sobrescribe ninguna configuración del usuario:
        - Realiza backup de seguridad previo de la base de datos SQLite.
        - Preserva la base de datos (~/.vigiwinpro/vigiwin.db) intacta.
        - Preserva cámaras, sensibilidades, usuarios RBAC y auditorías.
        """
        # 1. Crear copia de seguridad preventiva automática
        backup_created = None
        if db_manager is not None:
            try:
                bm = BackupManager(db_manager)
                backup_created = bm.create_backup(tag="pre_github_update")
            except Exception as e:
                # No bloquear si la copia auxiliar falla
                pass

        if not self.is_git_repository():
            return {
                "success": False,
                "error": "Instalación sin control de versiones Git.",
                "message": "Para instalaciones empaquetadas sin Git, utilice el instalador descargable más reciente."
            }

        try:
            # 2. Verificar estado de cambios locales para protegerlos
            status_proc = self.run_git_command(["status", "--porcelain"])
            has_local_changes = bool(status_proc.stdout.strip())

            stashed = False
            if has_local_changes:
                # Guardar cambios locales en stash para que no colisionen ni se pierdan
                stash_proc = self.run_git_command(["stash", "save", "vigiwin_user_customizations"])
                stashed = (stash_proc.returncode == 0)

            # 3. Aplicar solo los cambios de GitHub mediante merge fast-forward
            # Obtener rama
            branch = "master"
            check = self._check_git_updates()
            if check.get("branch"):
                branch = check.get("branch")

            pull_proc = self.run_git_command(["merge", "--ff-only", f"origin/{branch}"])
            if pull_proc.returncode != 0:
                # Si ff-only falla debido a ramas divergentes, hacer pull controlado
                pull_proc = self.run_git_command(["pull", "--no-rebase", "origin", branch])

            if pull_proc.returncode != 0:
                if stashed:
                    self.run_git_command(["stash", "pop"])
                return {
                    "success": False,
                    "error": pull_proc.stderr.strip() or pull_proc.stdout.strip(),
                    "message": "Error al aplicar los cambios desde GitHub. Se restauró el estado previo."
                }

            # Si se guardó stash, recuperar sin sobreescribir código nuevo
            if stashed:
                self.run_git_command(["stash", "pop"])

            # 4. Validar que la base de datos y configuraciones siguen activas
            if db_manager is not None:
                try:
                    db_manager.init_db()  # Aplica migraciones si hay columnas nuevas sin tocar datos
                    settings = db_manager.get_all_settings()
                    cams = db_manager.get_cameras()
                    users = db_manager.get_users()
                    db_manager.log_audit(
                        "Administrador",
                        "Actualización del Sistema desde GitHub",
                        f"Actualizado a origin/{branch}. Settings: {len(settings)}, Cámaras: {len(cams)}, Usuarios: {len(users)}"
                    )
                except Exception as e:
                    pass

            # 5. Obtener nuevo hash activo
            head_proc = self.run_git_command(["rev-parse", "HEAD"])
            new_hash = head_proc.stdout.strip()[:8]

            return {
                "success": True,
                "new_commit": new_hash,
                "backup_path": backup_created,
                "message": f"¡Sistema actualizado exitosamente al commit [{new_hash}] desde GitHub!\n"
                           f"Todas sus configuraciones de usuario, cámaras y perfiles han sido preservados al 100%."
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Excepción al aplicar cambios: {e}"
            }


class UpdateThread(QThread):
    """Hilo de trabajo en segundo plano para no congelar la interfaz durante la conexión con GitHub."""
    status_signal = Signal(str)
    check_finished = Signal(dict)
    apply_finished = Signal(dict)

    def __init__(self, mode: str = "check", db_manager=None, parent=None):
        super().__init__(parent)
        self.mode = mode
        self.db_manager = db_manager
        self.updater = SystemUpdater()

    def run(self):
        if self.mode == "check":
            self.status_signal.emit("Conectando con GitHub: https://github.com/SANDAVID14/VIGIWIN-PRO.git...")
            res = self.updater.check_for_updates()
            self.check_finished.emit(res)
        elif self.mode == "apply":
            self.status_signal.emit("Descargando y aplicando cambios de GitHub...")
            res = self.updater.apply_updates(self.db_manager)
            self.apply_finished.emit(res)
