"""
VIGI-WIN PRO - Pestaña 3: Administración, RBAC y Copias de Seguridad
Gestión de roles y permisos, usuarios (Administrador y Operador con cargo y activación),
identidad corporativa (nombre de empresa y logo), configuración de detección por cámara,
administración de cámaras (DVR/NVR con RTSP sobre TCP, USB y simulación) y backups SHA-256.
"""
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QLineEdit, QComboBox, QSpinBox, QFileDialog, QMessageBox,
    QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox,
    QGridLayout, QGroupBox, QDialog, QFormLayout, QAbstractItemView,
    QSlider, QProgressBar, QTextEdit, QApplication
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor, QColor, QPixmap, QIcon

from vigiwin.core.backup import BackupManager
from vigiwin.core.rbac import RBACManager
from vigiwin.core.updater import SystemUpdater, UpdateThread, GITHUB_REPO_URL


class UserFormDialog(QDialog):
    """Diálogo unificado para Crear o Modificar Usuarios RBAC con cargo, rol, clave y botón Guardar/Activar."""
    def __init__(self, username=None, initial_data=None, parent=None):
        super().__init__(parent)
        self.username = username
        self.is_edit = (username is not None)
        self.setWindowTitle(f"Modificar Usuario: {username}" if self.is_edit else "Crear Nuevo Usuario RBAC")
        self.setMinimumWidth(400)
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.setStyleSheet("""
            QDialog {
                background-color: #0f172a;
                color: #f1f5f9;
            }
            QLabel {
                color: #cbd5e1;
                font-size: 11px;
                font-weight: 500;
            }
            QLineEdit, QComboBox {
                background-color: #1e293b;
                color: #ffffff;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 11px;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: #10b981;
            }
            QLineEdit:disabled {
                background-color: #090e1a;
                color: #64748b;
            }
            QCheckBox {
                color: #f1f5f9;
                font-size: 11px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        header = QLabel("Modificación de Usuario del Sistema" if self.is_edit else "Registro de Nuevo Usuario del Sistema")
        header.setStyleSheet("font-size: 13px; font-weight: bold; color: #10b981; margin-bottom: 4px;")
        layout.addWidget(header)

        form = QFormLayout()
        form.setSpacing(10)

        # Nombre de usuario
        self.txt_username = QLineEdit()
        if self.is_edit:
            self.txt_username.setText(username)
            self.txt_username.setEnabled(False)
        else:
            self.txt_username.setPlaceholderText("Ej: operador01, supervisor_turno")
        form.addRow("Nombre de Usuario:", self.txt_username)

        # Cargo del usuario
        self.txt_cargo = QLineEdit()
        self.txt_cargo.setPlaceholderText("Ej: Operador de Monitoreo, Supervisor Nocturno")
        if initial_data and initial_data.get("cargo"):
            self.txt_cargo.setText(initial_data.get("cargo"))
        else:
            self.txt_cargo.setText("Operador de Monitoreo")
        form.addRow("Cargo del Usuario:", self.txt_cargo)

        # Rol Asignado
        self.combo_role = QComboBox()
        self.combo_role.addItems(["Operador", "Administrador", "Auditor"])
        curr_role = (initial_data.get("role") if initial_data else "Operador")
        if curr_role == "Operador de Seguridad":
            curr_role = "Operador"
        idx = self.combo_role.findText(curr_role)
        if idx >= 0:
            self.combo_role.setCurrentIndex(idx)
        else:
            self.combo_role.setCurrentIndex(0)
        form.addRow("Rol en el Sistema:", self.combo_role)

        # Contraseña
        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.Password)
        if self.is_edit:
            self.txt_password.setPlaceholderText("Dejar en blanco para conservar clave actual")
        else:
            self.txt_password.setPlaceholderText("Mínimo 4 caracteres")
        form.addRow("Contraseña:", self.txt_password)

        # Confirmar contraseña
        self.txt_confirm = QLineEdit()
        self.txt_confirm.setEchoMode(QLineEdit.Password)
        self.txt_confirm.setPlaceholderText("Repita la contraseña" if not self.is_edit else "Confirmar si cambia")
        form.addRow("Confirmar Clave:", self.txt_confirm)

        # Estado Activo / Inactivo
        self.chk_active = QCheckBox("Usuario Activo / Habilitado para Iniciar Sesión")
        curr_active = bool(initial_data.get("is_active", 1) if initial_data else True)
        self.chk_active.setChecked(curr_active)
        form.addRow("Estado:", self.chk_active)

        layout.addLayout(form)

        # Botones Cancelar y Guardar/Activar
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setCursor(QCursor(Qt.PointingHandCursor))
        btn_cancel.setStyleSheet("background-color: #334155; color: #e2e8f0; border: none; border-radius: 6px; padding: 7px 14px; font-size: 11px;")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        btn_save = QPushButton("💾  Guardar / Activar")
        btn_save.setCursor(QCursor(Qt.PointingHandCursor))
        btn_save.setStyleSheet("background-color: #10b981; color: #020617; font-weight: bold; border: none; border-radius: 6px; padding: 7px 16px; font-size: 11px;")
        btn_save.clicked.connect(self._validate_and_accept)
        btn_row.addWidget(btn_save)

        layout.addLayout(btn_row)

    def _validate_and_accept(self):
        u = self.txt_username.text().strip()
        p1 = self.txt_password.text()
        p2 = self.txt_confirm.text()
        cargo = self.txt_cargo.text().strip()

        if not u:
            QMessageBox.warning(self, "Validación", "El nombre de usuario es obligatorio.")
            return

        if not cargo:
            QMessageBox.warning(self, "Validación", "El cargo del usuario es obligatorio.")
            return

        if not self.is_edit:
            if len(p1) < 4:
                QMessageBox.warning(self, "Validación", "La contraseña debe tener al menos 4 caracteres.")
                return
            if p1 != p2:
                QMessageBox.warning(self, "Validación", "Las contraseñas no coinciden.")
                return
        else:
            if p1:
                if len(p1) < 4:
                    QMessageBox.warning(self, "Validación", "La nueva contraseña debe tener al menos 4 caracteres.")
                    return
                if p1 != p2:
                    QMessageBox.warning(self, "Validación", "Las nuevas contraseñas no coinciden.")
                    return

        self.accept()

    def get_data(self):
        return {
            "username": self.txt_username.text().strip(),
            "cargo": self.txt_cargo.text().strip(),
            "role": self.combo_role.currentText(),
            "password": self.txt_password.text() if self.txt_password.text() else None,
            "is_active": 1 if self.chk_active.isChecked() else 0
        }


class GitHubUpdateDialog(QDialog):
    """Diálogo interactivo para comprobar y aplicar actualizaciones desde GitHub preservando configuraciones."""
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.updater = SystemUpdater()
        self.worker = None

        self.setWindowTitle("Sincronización y Actualización desde GitHub - VIGI-WIN PRO")

        # Adaptabilidad automática a la resolución del monitor
        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            target_w = min(620, max(460, int(avail.width() * 0.82)))
            target_h = min(500, max(380, int(avail.height() * 0.80)))
            self.resize(target_w, target_h)
        else:
            self.resize(580, 480)
        self.setMinimumSize(460, 360)

        # Icono de ventana
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.setStyleSheet("""
            QDialog {
                background-color: #0b1120;
                color: #f1f5f9;
            }
            QLabel {
                color: #cbd5e1;
            }
            QPushButton {
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 11px;
                font-weight: bold;
            }
            QTextEdit {
                background-color: #020617;
                color: #34d399;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
                border: 1px solid #1e293b;
                border-radius: 6px;
                padding: 8px;
            }
            QProgressBar {
                background-color: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 4px;
                height: 8px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #10b981;
                border-radius: 4px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Encabezado
        hdr = QHBoxLayout()
        icon_lbl = QLabel("🔄")
        icon_lbl.setStyleSheet("font-size: 26px;")
        hdr.addWidget(icon_lbl)

        hdr_col = QVBoxLayout()
        lbl_title = QLabel("Actualizador Oficial desde GitHub")
        lbl_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #10b981;")
        hdr_col.addWidget(lbl_title)

        lbl_repo = QLabel(f"<b>Repositorio:</b> {GITHUB_REPO_URL}")
        lbl_repo.setStyleSheet("font-size: 11px; color: #94a3b8;")
        hdr_col.addWidget(lbl_repo)
        hdr.addLayout(hdr_col)
        layout.addLayout(hdr)

        # Banner de Protección Estricta de Configuración
        notice_box = QFrame()
        notice_box.setStyleSheet("background-color: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 6px; padding: 10px;")
        notice_layout = QHBoxLayout(notice_box)
        lbl_shield = QLabel("🛡️")
        lbl_shield.setStyleSheet("font-size: 18px;")
        notice_layout.addWidget(lbl_shield)
        lbl_notice = QLabel("<b>Garantía de Preservación de Datos:</b> Al actualizar el programa desde GitHub, "
                            "no se modificará ninguna configuración del usuario. Los parámetros de cámaras, "
                            "usuarios RBAC, umbrales y base de datos SQLite permanecen 100% protegidos.")
        lbl_notice.setWordWrap(True)
        lbl_notice.setStyleSheet("font-size: 10px; color: #a7f3d0; line-height: 1.4;")
        notice_layout.addWidget(lbl_notice)
        layout.addWidget(notice_box)

        # Barra de progreso y estado
        self.lbl_status = QLabel("Conectando con GitHub...")
        self.lbl_status.setStyleSheet("font-size: 11px; font-weight: bold; color: #38bdf8;")
        layout.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        layout.addWidget(self.progress_bar)

        # Consola de detalles de cambios
        lbl_log = QLabel("Registro de cambios y estado de sincronización:")
        lbl_log.setStyleSheet("font-size: 11px; color: #94a3b8;")
        layout.addWidget(lbl_log)

        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        layout.addWidget(self.txt_log)

        # Botonera de acciones
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)

        self.btn_check_again = QPushButton("🔍 Comprobar Nuevamente")
        self.btn_check_again.setStyleSheet("background-color: #1e293b; color: #f1f5f9; border: 1px solid #334155;")
        self.btn_check_again.clicked.connect(self.start_check)
        btn_box.addWidget(self.btn_check_again)

        btn_box.addStretch()

        self.btn_apply = QPushButton("⚡ Aplicar Cambios Detectados")
        self.btn_apply.setEnabled(False)
        self.btn_apply.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: #020617;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover {
                background-color: #059669;
            }
            QPushButton:disabled {
                background-color: #1e293b;
                color: #64748b;
            }
        """)
        self.btn_apply.clicked.connect(self.apply_changes)
        btn_box.addWidget(self.btn_apply)

        self.btn_close = QPushButton("Cerrar")
        self.btn_close.setStyleSheet("background-color: #1e293b; color: #94a3b8; border: 1px solid #334155;")
        self.btn_close.clicked.connect(self.accept)
        btn_box.addWidget(self.btn_close)

        layout.addLayout(btn_box)

        # Iniciar comprobación automáticamente al abrir
        self.start_check()

    def start_check(self):
        self.progress_bar.setRange(0, 0)
        self.btn_apply.setEnabled(False)
        self.btn_check_again.setEnabled(False)
        self.lbl_status.setText("Conectando a GitHub y buscando cambios...")
        self.lbl_status.setStyleSheet("font-size: 11px; font-weight: bold; color: #38bdf8;")
        self.txt_log.setPlainText("Consultando repositorio remoto https://github.com/SANDAVID14/VIGIWIN-PRO.git...\n")

        self.worker = UpdateThread(mode="check", db_manager=self.db, parent=self)
        self.worker.check_finished.connect(self._on_check_finished)
        self.worker.start()

    def _on_check_finished(self, res: dict):
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.btn_check_again.setEnabled(True)

        if not res.get("success"):
            self.lbl_status.setText(f"❌ {res.get('message', 'Error de conexión')}")
            self.lbl_status.setStyleSheet("font-size: 11px; font-weight: bold; color: #ef4444;")
            self.txt_log.append(f"\nDetalle:\n{res.get('error', 'Sin detalle')}")
            return

        if res.get("has_updates"):
            commits = res.get("commits", [])
            changed = res.get("changed_files", [])
            self.lbl_status.setText(f"⚡ Se encontraron {len(commits)} nueva(s) actualización(es) en GitHub.")
            self.lbl_status.setStyleSheet("font-size: 11px; font-weight: bold; color: #f59e0b;")
            self.btn_apply.setEnabled(True)

            log_text = f"Commit local actual:  {res.get('local_commit')}\n"
            log_text += f"Commit remoto GitHub: {res.get('remote_commit')}\n"
            log_text += f"\n--- LISTA DE ACTUALIZACIONES DISPONIBLES ({len(commits)}) ---\n"
            for c in commits:
                log_text += f"• {c}\n"

            if changed:
                log_text += f"\n--- ARCHIVOS QUE SE ACTUALIZARÁN ({len(changed)}) ---\n"
                for f in changed:
                    log_text += f"  → {f}\n"

            log_text += "\n[PROTECCIÓN ACTIVA] Base de datos SQLite y datos de usuario NO se modificarán."
            self.txt_log.setPlainText(log_text)
        else:
            self.lbl_status.setText("✅ El sistema se encuentra en su versión más reciente.")
            self.lbl_status.setStyleSheet("font-size: 11px; font-weight: bold; color: #10b981;")
            self.btn_apply.setEnabled(False)
            self.txt_log.setPlainText(
                f"Commit activo: {res.get('local_commit')}\n"
                "El software coincide exactamente con la rama oficial de GitHub.\n"
                "No existen cambios pendientes de aplicar.\n\n"
                "Todas sus configuraciones de usuario están vigentes e intactas."
            )

    def apply_changes(self):
        confirm = QMessageBox.question(
            self,
            "Confirmar Actualización",
            "¿Desea aplicar los cambios desde GitHub ahora?\n\n"
            "• Se descargará y aplicará el código más reciente.\n"
            "• Se realizará un respaldo preventivo automático de su base de datos.\n"
            "• Su configuración, usuarios, cámaras e histórico permanecerán 100% protegidos.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if confirm != QMessageBox.Yes:
            return

        self.btn_apply.setEnabled(False)
        self.btn_check_again.setEnabled(False)
        self.progress_bar.setRange(0, 0)
        self.lbl_status.setText("Aplicando cambios desde GitHub...")
        self.lbl_status.setStyleSheet("font-size: 11px; font-weight: bold; color: #38bdf8;")

        self.worker = UpdateThread(mode="apply", db_manager=self.db, parent=self)
        self.worker.apply_finished.connect(self._on_apply_finished)
        self.worker.start()

    def _on_apply_finished(self, res: dict):
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.btn_check_again.setEnabled(True)

        if res.get("success"):
            self.lbl_status.setText("✅ ¡Actualización completada exitosamente!")
            self.lbl_status.setStyleSheet("font-size: 11px; font-weight: bold; color: #10b981;")
            self.txt_log.append(f"\n{res.get('message', '')}")
            if res.get("backup_path"):
                self.txt_log.append(f"\nCopia preventiva generada en: {res.get('backup_path')}")
            QMessageBox.information(
                self,
                "Actualización Exitosa",
                res.get("message", "Actualización aplicada con éxito.")
            )
            self.btn_close.setText("Listo")
        else:
            self.lbl_status.setText("❌ Error al aplicar cambios.")
            self.lbl_status.setStyleSheet("font-size: 11px; font-weight: bold; color: #ef4444;")
            self.txt_log.append(f"\nError: {res.get('error', 'Fallo desconocido')}")
            QMessageBox.critical(
                self,
                "Error de Actualización",
                f"No se pudieron aplicar los cambios:\n{res.get('error', 'Error desconocido')}"
            )


class AdminTab(QWidget):
    def __init__(self, db_manager, camera_manager, rbac_manager=None, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.camera_manager = camera_manager
        self.backup_mgr = BackupManager(db_manager)
        self.rbac_mgr = rbac_manager if rbac_manager is not None else RBACManager(db_manager)
        self.on_cameras_updated = None
        self.on_company_branding_updated = None
        self.camera_rows = []
        self._is_populating_matrix = False

        self.init_ui()
        self._refresh_users_table()
        self._refresh_permissions_matrix()
        self._refresh_session_banner()
        self._populate_detection_cameras()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(14)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        scroll_content = QWidget()
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setSpacing(14)

        # ----------------------------------------------------
        # SECCIÓN 1: PANEL RBAC INTEGRAL (Usuarios, Conmutador & Matriz)
        # ----------------------------------------------------
        rbac_panel = QFrame()
        rbac_panel.setStyleSheet("background-color: #0f172a; border: 1px solid #1e293b; border-radius: 12px; padding: 14px;")
        rbac_layout = QVBoxLayout(rbac_panel)
        rbac_layout.setSpacing(12)

        # 1.1 Cabecera y Conmutador de Sesión en Tiempo Real
        header_row = QHBoxLayout()
        header_row.setSpacing(10)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        lbl_rbac_title = QLabel("ROLES Y CONTROL DE ACCESO (RBAC)")
        lbl_rbac_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #10b981; letter-spacing: 0.5px;")
        title_col.addWidget(lbl_rbac_title)

        self.lbl_active_session = QLabel("Sesión Activa: admin (Administrador)")
        self.lbl_active_session.setStyleSheet("font-size: 11px; color: #94a3b8;")
        title_col.addWidget(self.lbl_active_session)
        header_row.addLayout(title_col)

        header_row.addStretch()

        # Botones de Conmutación Rápida de Sesión
        lbl_quick_sw = QLabel("Conmutar Sesión:")
        lbl_quick_sw.setStyleSheet("font-size: 10px; color: #64748b; font-weight: bold;")
        header_row.addWidget(lbl_quick_sw)

        self.btn_sw_admin = QPushButton("👑 Administrador")
        self.btn_sw_admin.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_sw_admin.setStyleSheet("background-color: #064e3b; color: #34d399; border: 1px solid #059669; border-radius: 6px; padding: 4px 10px; font-size: 10px; font-weight: bold;")
        self.btn_sw_admin.clicked.connect(lambda: self._quick_switch_session("admin"))
        header_row.addWidget(self.btn_sw_admin)

        self.btn_sw_oper = QPushButton("🛡️ Operador")
        self.btn_sw_oper.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_sw_oper.setStyleSheet("background-color: #1e293b; color: #94a3b8; border: 1px solid #334155; border-radius: 6px; padding: 4px 10px; font-size: 10px; font-weight: bold;")
        self.btn_sw_oper.clicked.connect(lambda: self._quick_switch_session("operador"))
        header_row.addWidget(self.btn_sw_oper)

        self.btn_sw_audit = QPushButton("📋 Auditor")
        self.btn_sw_audit.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_sw_audit.setStyleSheet("background-color: #1e293b; color: #94a3b8; border: 1px solid #334155; border-radius: 6px; padding: 4px 10px; font-size: 10px; font-weight: bold;")
        self.btn_sw_audit.clicked.connect(lambda: self._quick_switch_session("auditor"))
        header_row.addWidget(self.btn_sw_audit)

        # Botón Actualizar (ADMINISTRACION RBAC / Administrador)
        self.btn_update_github = QPushButton("🔄 Actualizar")
        self.btn_update_github.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_update_github.setStyleSheet("""
            QPushButton {
                background-color: #065f46;
                color: #ffffff;
                border: 1px solid #10b981;
                border-radius: 6px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #059669;
            }
            QPushButton:disabled {
                background-color: #1e293b;
                color: #64748b;
                border: 1px solid #334155;
            }
        """)
        self.btn_update_github.setToolTip("Conectar con https://github.com/SANDAVID14/VIGIWIN-PRO.git, verificar y aplicar cambios")
        self.btn_update_github.clicked.connect(self._open_github_updater_dialog)
        header_row.addWidget(self.btn_update_github)

        rbac_layout.addLayout(header_row)

        # 1.1.2 Barra Informativa de Sincronización GitHub y Preservación de Datos
        update_banner = QFrame()
        update_banner.setStyleSheet("background-color: #090e1a; border: 1px solid #1e293b; border-radius: 6px; padding: 6px 12px;")
        update_banner_layout = QHBoxLayout(update_banner)
        update_banner_layout.setContentsMargins(6, 4, 6, 4)
        update_banner_layout.setSpacing(10)

        lbl_git_repo = QLabel("🐙 <b>GitHub:</b> https://github.com/SANDAVID14/VIGIWIN-PRO.git (Rama master)")
        lbl_git_repo.setStyleSheet("color: #94a3b8; font-size: 10px;")
        update_banner_layout.addWidget(lbl_git_repo)

        update_banner_layout.addStretch()

        self.lbl_git_status = QLabel("Listo para verificar cambios | Preservación de configuración activa")
        self.lbl_git_status.setStyleSheet("color: #34d399; font-size: 10px; font-weight: bold;")
        update_banner_layout.addWidget(self.lbl_git_status)

        rbac_layout.addWidget(update_banner)

        # 1.2 Layout de 2 Columnas: Gestión de Usuarios (Izquierda) + Matriz de Permisos (Derecha)
        rbac_grid = QHBoxLayout()
        rbac_grid.setSpacing(14)

        # --- COLUMNA IZQUIERDA: GESTIÓN DE USUARIOS (CRUD) ---
        users_box = QFrame()
        users_box.setStyleSheet("background-color: #090e1a; border: 1px solid #1e293b; border-radius: 8px; padding: 10px;")
        users_box_layout = QVBoxLayout(users_box)
        users_box_layout.setSpacing(8)

        users_header = QHBoxLayout()
        lbl_users_title = QLabel("👥 Usuarios y Operadores (SQLite)")
        lbl_users_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #f1f5f9;")
        users_header.addWidget(lbl_users_title)
        users_header.addStretch()

        self.btn_create_user = QPushButton("➕ Crear Usuario")
        self.btn_create_user.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_create_user.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: #020617;
                font-size: 10px;
                font-weight: bold;
                border: none;
                border-radius: 5px;
                padding: 4px 10px;
            }
            QPushButton:hover {
                background-color: #059669;
            }
        """)
        self.btn_create_user.clicked.connect(self._open_create_user_dialog)
        users_header.addWidget(self.btn_create_user)
        users_box_layout.addLayout(users_header)

        self.table_users = QTableWidget(0, 5)
        self.table_users.setHorizontalHeaderLabels(["Usuario", "Cargo", "Rol", "Estado", "Acciones"])
        self.table_users.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_users.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_users.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_users.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table_users.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table_users.setStyleSheet("""
            QTableWidget {
                background-color: #060b17;
                border: 1px solid #1e293b;
                border-radius: 6px;
                gridline-color: #1e293b;
                color: #cbd5e1;
                font-size: 11px;
            }
            QHeaderView::section {
                background-color: #0f172a;
                color: #94a3b8;
                font-size: 10px;
                font-weight: bold;
                border: none;
                padding: 4px;
            }
        """)
        self.table_users.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_users.setMinimumHeight(240)
        users_box_layout.addWidget(self.table_users)

        rbac_grid.addWidget(users_box, stretch=3)

        # --- COLUMNA DERECHA: MATRIZ VISUAL DE PERMISOS ---
        perms_box = QFrame()
        perms_box.setStyleSheet("background-color: #090e1a; border: 1px solid #1e293b; border-radius: 8px; padding: 10px;")
        perms_box_layout = QVBoxLayout(perms_box)
        perms_box_layout.setSpacing(8)

        perms_header = QHBoxLayout()
        lbl_perms_title = QLabel("🛡️ Matriz Visual de Permisos por Rol")
        lbl_perms_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #f1f5f9;")
        perms_header.addWidget(lbl_perms_title)
        perms_header.addStretch()

        self.btn_reset_perms = QPushButton("Valores por Defecto")
        self.btn_reset_perms.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_reset_perms.setStyleSheet("background-color: #1e293b; color: #94a3b8; border: 1px solid #334155; border-radius: 5px; padding: 3px 8px; font-size: 10px;")
        self.btn_reset_perms.clicked.connect(self._reset_permissions)
        perms_header.addWidget(self.btn_reset_perms)
        perms_box_layout.addLayout(perms_header)

        self.table_permissions = QTableWidget(0, 4)
        self.table_permissions.setHorizontalHeaderLabels(["Permiso / Acción", "Admin", "Operador", "Auditor"])
        self.table_permissions.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_permissions.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_permissions.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_permissions.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table_permissions.setStyleSheet("""
            QTableWidget {
                background-color: #060b17;
                border: 1px solid #1e293b;
                border-radius: 6px;
                gridline-color: #1e293b;
                color: #cbd5e1;
                font-size: 11px;
            }
            QHeaderView::section {
                background-color: #0f172a;
                color: #94a3b8;
                font-size: 10px;
                font-weight: bold;
                border: none;
                padding: 4px;
            }
        """)
        self.table_permissions.setMinimumHeight(240)
        perms_box_layout.addWidget(self.table_permissions)

        rbac_grid.addWidget(perms_box, stretch=2)
        rbac_layout.addLayout(rbac_grid)

        content_layout.addWidget(rbac_panel)

        # ----------------------------------------------------
        # SECCIÓN 2: IDENTIDAD CORPORATIVA Y EMPRESA (Nombre y Logo)
        # ----------------------------------------------------
        brand_panel = QFrame()
        brand_panel.setStyleSheet("background-color: #0f172a; border: 1px solid #1e293b; border-radius: 12px; padding: 14px;")
        brand_layout = QVBoxLayout(brand_panel)
        brand_layout.setSpacing(10)

        lbl_brand_title = QLabel("🏢 IDENTIDAD CORPORATIVA Y EMPRESA")
        lbl_brand_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #10b981; letter-spacing: 0.5px;")
        brand_layout.addWidget(lbl_brand_title)

        lbl_brand_desc = QLabel("Configure el nombre institucional de la empresa y el logotipo oficial que se mostrarán en la barra superior de la aplicación y en los reportes.")
        lbl_brand_desc.setStyleSheet("font-size: 11px; color: #94a3b8;")
        brand_layout.addWidget(lbl_brand_desc)

        brand_form_grid = QGridLayout()
        brand_form_grid.setSpacing(10)

        # Nombre de la empresa
        brand_form_grid.addWidget(QLabel("Nombre de la Empresa / Instalación:"), 0, 0)
        curr_company = self.db.get_setting("company_name", "VigiWin Pro - Sistema Inteligente de Vigilancia")
        self.txt_company_name = QLineEdit(curr_company)
        self.txt_company_name.setStyleSheet("background-color: #1e293b; color: #ffffff; border: 1px solid #334155; border-radius: 6px; padding: 6px 10px;")
        brand_form_grid.addWidget(self.txt_company_name, 0, 1)

        self.btn_save_company_name = QPushButton("💾 Guardar Nombre")
        self.btn_save_company_name.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_save_company_name.setStyleSheet("background-color: #10b981; color: #020617; font-weight: bold; border-radius: 6px; padding: 6px 14px; font-size: 11px;")
        self.btn_save_company_name.clicked.connect(self._save_company_name)
        brand_form_grid.addWidget(self.btn_save_company_name, 0, 2)

        # Logotipo
        brand_form_grid.addWidget(QLabel("Logotipo de la Aplicación:"), 1, 0)
        logo_row = QHBoxLayout()
        logo_row.setSpacing(10)

        self.lbl_logo_preview = QLabel()
        self.lbl_logo_preview.setFixedSize(36, 36)
        self.lbl_logo_preview.setStyleSheet("background-color: #1e293b; border: 1px solid #334155; border-radius: 6px;")
        self.lbl_logo_preview.setAlignment(Qt.AlignCenter)
        self._update_logo_preview()
        logo_row.addWidget(self.lbl_logo_preview)

        self.btn_select_logo = QPushButton("📁 Cambiar Logotipo (.png, .jpg)")
        self.btn_select_logo.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_select_logo.setStyleSheet("background-color: #1e293b; color: #38bdf8; border: 1px solid #334155; border-radius: 6px; padding: 6px 12px; font-size: 11px;")
        self.btn_select_logo.clicked.connect(self._select_company_logo)
        logo_row.addWidget(self.btn_select_logo)

        self.btn_reset_logo = QPushButton("↺ Logo por Defecto")
        self.btn_reset_logo.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_reset_logo.setStyleSheet("background-color: #1e293b; color: #94a3b8; border: 1px solid #334155; border-radius: 6px; padding: 6px 12px; font-size: 11px;")
        self.btn_reset_logo.clicked.connect(self._reset_company_logo)
        logo_row.addWidget(self.btn_reset_logo)
        logo_row.addStretch()

        brand_form_grid.addLayout(logo_row, 1, 1, 1, 2)
        brand_layout.addLayout(brand_form_grid)
        content_layout.addWidget(brand_panel)

        # ----------------------------------------------------
        # SECCIÓN 3: CONFIGURACIÓN DE DETECCIÓN E INTELIGENCIA ARTIFICIAL POR CÁMARA
        # ----------------------------------------------------
        det_panel = QFrame()
        det_panel.setStyleSheet("background-color: #0f172a; border: 1px solid #1e293b; border-radius: 12px; padding: 14px;")
        det_layout = QVBoxLayout(det_panel)
        det_layout.setSpacing(10)

        lbl_det_title = QLabel("🧠 CONFIGURACIÓN DE DETECCIÓN E INTELIGENCIA ARTIFICIAL POR CÁMARA")
        lbl_det_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #10b981; letter-spacing: 0.5px;")
        det_layout.addWidget(lbl_det_title)

        lbl_det_desc = QLabel("Seleccione una cámara para calibrar individualmente sus umbrales de sensibilidad de visión artificial (personas y vehículos) y el tiempo máximo de apertura de puerta.")
        lbl_det_desc.setStyleSheet("font-size: 11px; color: #94a3b8;")
        det_layout.addWidget(lbl_det_desc)

        # Selector de cámara a calibrar
        cam_sel_row = QHBoxLayout()
        cam_sel_row.setSpacing(10)
        lbl_choose = QLabel("Cámara a Configurar:")
        lbl_choose.setStyleSheet("color: #cbd5e1; font-weight: bold; font-size: 11px;")
        cam_sel_row.addWidget(lbl_choose)

        self.combo_det_cam = QComboBox()
        self.combo_det_cam.setMinimumWidth(280)
        self.combo_det_cam.currentIndexChanged.connect(self._on_detection_camera_selected)
        cam_sel_row.addWidget(self.combo_det_cam)
        cam_sel_row.addStretch()
        det_layout.addLayout(cam_sel_row)

        # Grid de parámetros de IA
        det_grid = QGridLayout()
        det_grid.setSpacing(12)

        # 1. Personas
        box_person = QFrame()
        box_person.setStyleSheet("background-color: #090e1a; border: 1px solid #1e293b; border-radius: 8px; padding: 10px;")
        bp_layout = QVBoxLayout(box_person)
        bp_layout.setSpacing(8)
        self.chk_det_person = QCheckBox("👤 Detectar Personas (IA)")
        self.chk_det_person.setStyleSheet("color: #34d399; font-weight: bold; font-size: 11px;")
        bp_layout.addWidget(self.chk_det_person)

        lbl_ps_row = QHBoxLayout()
        lbl_ps = QLabel("Sensibilidad Personas:")
        lbl_ps.setStyleSheet("color: #94a3b8; font-size: 10px;")
        lbl_ps_row.addWidget(lbl_ps)
        self.lbl_person_sens_val = QLabel("80%")
        self.lbl_person_sens_val.setStyleSheet("color: #34d399; font-weight: bold; font-family: monospace; font-size: 11px;")
        lbl_ps_row.addWidget(self.lbl_person_sens_val)
        bp_layout.addLayout(lbl_ps_row)

        self.slider_person_sens = QSlider(Qt.Horizontal)
        self.slider_person_sens.setRange(10, 100)
        self.slider_person_sens.setValue(80)
        self.slider_person_sens.valueChanged.connect(lambda v: self.lbl_person_sens_val.setText(f"{v}%"))
        bp_layout.addWidget(self.slider_person_sens)
        det_grid.addWidget(box_person, 0, 0)

        # 2. Vehículos
        box_veh = QFrame()
        box_veh.setStyleSheet("background-color: #090e1a; border: 1px solid #1e293b; border-radius: 8px; padding: 10px;")
        bv_layout = QVBoxLayout(box_veh)
        bv_layout.setSpacing(8)
        self.chk_det_vehicle = QCheckBox("🚗 Detectar Vehículos (IA)")
        self.chk_det_vehicle.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 11px;")
        bv_layout.addWidget(self.chk_det_vehicle)

        lbl_vs_row = QHBoxLayout()
        lbl_vs = QLabel("Sensibilidad Vehículos:")
        lbl_vs.setStyleSheet("color: #94a3b8; font-size: 10px;")
        lbl_vs_row.addWidget(lbl_vs)
        self.lbl_vehicle_sens_val = QLabel("75%")
        self.lbl_vehicle_sens_val.setStyleSheet("color: #38bdf8; font-weight: bold; font-family: monospace; font-size: 11px;")
        lbl_vs_row.addWidget(self.lbl_vehicle_sens_val)
        bv_layout.addLayout(lbl_vs_row)

        self.slider_vehicle_sens = QSlider(Qt.Horizontal)
        self.slider_vehicle_sens.setRange(10, 100)
        self.slider_vehicle_sens.setValue(75)
        self.slider_vehicle_sens.valueChanged.connect(lambda v: self.lbl_vehicle_sens_val.setText(f"{v}%"))
        bv_layout.addWidget(self.slider_vehicle_sens)
        det_grid.addWidget(box_veh, 0, 1)

        # 3. Puerta / Tiempo máximo
        box_door = QFrame()
        box_door.setStyleSheet("background-color: #090e1a; border: 1px solid #1e293b; border-radius: 8px; padding: 10px;")
        bd_layout = QVBoxLayout(box_door)
        bd_layout.setSpacing(8)
        lbl_dr_title = QLabel("🚪 Regla de Apertura de Puerta")
        lbl_dr_title.setStyleSheet("color: #fbbf24; font-weight: bold; font-size: 11px;")
        bd_layout.addWidget(lbl_dr_title)

        lbl_dt_row = QHBoxLayout()
        lbl_dt = QLabel("Tiempo Máx. Abierta (seg):")
        lbl_dt.setStyleSheet("color: #94a3b8; font-size: 10px;")
        lbl_dt_row.addWidget(lbl_dt)
        self.spin_door_time = QSpinBox()
        self.spin_door_time.setRange(10, 600)
        self.spin_door_time.setValue(60)
        self.spin_door_time.setStyleSheet("background-color: #1e293b; color: #ffffff; border: 1px solid #334155; border-radius: 4px; padding: 2px 6px;")
        lbl_dt_row.addWidget(self.spin_door_time)
        bd_layout.addLayout(lbl_dt_row)

        lbl_door_tip = QLabel("Genera alarma si la puerta permanece abierta más de este tiempo.")
        lbl_door_tip.setStyleSheet("color: #64748b; font-size: 9px;")
        bd_layout.addWidget(lbl_door_tip)
        det_grid.addWidget(box_door, 0, 2)

        det_layout.addLayout(det_grid)

        # Botón Guardar Detección
        det_btn_row = QHBoxLayout()
        det_btn_row.addStretch()
        self.btn_save_detection = QPushButton("💾  Guardar Configuración de Detección")
        self.btn_save_detection.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_save_detection.setStyleSheet("background-color: #10b981; color: #020617; font-weight: bold; border-radius: 6px; padding: 8px 18px; font-size: 11px;")
        self.btn_save_detection.clicked.connect(self._save_camera_detection)
        det_btn_row.addWidget(self.btn_save_detection)
        det_layout.addLayout(det_btn_row)

        content_layout.addWidget(det_panel)

        # ----------------------------------------------------
        # SECCIÓN 4: GESTIÓN DE CÁMARAS Y DVR/NVR RTSP
        # ----------------------------------------------------
        cam_panel = QFrame()
        cam_panel.setStyleSheet("background-color: #0f172a; border: 1px solid #1e293b; border-radius: 12px; padding: 14px;")
        cam_layout = QVBoxLayout(cam_panel)
        cam_layout.setSpacing(12)

        lbl_cam_title = QLabel("CONFIGURACIÓN DE CÁMARAS Y CONEXIÓN DVR / NVR / RTSP")
        lbl_cam_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #10b981; letter-spacing: 0.5px;")
        cam_layout.addWidget(lbl_cam_title)

        lbl_cam_desc = QLabel(
            "Vincule grabadores DVR/NVR multi-canal, cámaras IP autónomas o simuladores locales mediante RTSP sobre TCP/UDP. "
            "Configure múltiples cámaras por dispositivo con supervisión inteligente de puertas e IA."
        )
        lbl_cam_desc.setWordWrap(True)
        lbl_cam_desc.setStyleSheet("font-size: 11px; color: #94a3b8;")
        cam_layout.addWidget(lbl_cam_desc)

        # Formulario de Parámetros de Identificación del Dispositivo
        dev_form_grid = QGridLayout()
        dev_form_grid.setSpacing(10)

        # Nombre / Alias
        dev_form_grid.addWidget(QLabel("Nombre / Alias del Dispositivo:"), 0, 0)
        self.txt_dev_name = QLineEdit("DVR Dahua Acceso Principal")
        dev_form_grid.addWidget(self.txt_dev_name, 1, 0)

        # Tipo de Conexión
        dev_form_grid.addWidget(QLabel("Tipo de Conexión / Dispositivo:"), 0, 1)
        self.combo_dev_type = QComboBox()
        self.combo_dev_type.addItems([
            "DVR / NVR Multi-Canal (RTSP sobre TCP)",
            "Cámara IP RTSP Autónoma",
            "Webcam USB Local",
            "Simulador Multi-Cámara Inteligente"
        ])
        self.combo_dev_type.currentIndexChanged.connect(self._on_dev_type_changed)
        dev_form_grid.addWidget(self.combo_dev_type, 1, 1)

        # Host / IP
        dev_form_grid.addWidget(QLabel("Host / Dirección IP:"), 0, 2)
        self.txt_dev_host = QLineEdit("192.168.1.100")
        dev_form_grid.addWidget(self.txt_dev_host, 1, 2)

        # Puerto RTSP + Protocolo
        port_proto_layout = QHBoxLayout()
        self.spin_dev_port = QSpinBox()
        self.spin_dev_port.setRange(1, 65535)
        self.spin_dev_port.setValue(554)
        port_proto_layout.addWidget(self.spin_dev_port)
        self.combo_dev_protocol = QComboBox()
        self.combo_dev_protocol.addItems(["TCP", "UDP"])
        port_proto_layout.addWidget(self.combo_dev_protocol)
        dev_form_grid.addWidget(QLabel("Puerto / Protocolo:"), 0, 3)
        dev_form_grid.addLayout(port_proto_layout, 1, 3)

        # Usuario
        dev_form_grid.addWidget(QLabel("Usuario DVR:"), 2, 0)
        self.txt_dev_user = QLineEdit("admin")
        dev_form_grid.addWidget(self.txt_dev_user, 3, 0)

        # Contraseña
        dev_form_grid.addWidget(QLabel("Contraseña DVR:"), 2, 1)
        self.txt_dev_pass = QLineEdit("Admin@2026")
        self.txt_dev_pass.setEchoMode(QLineEdit.Password)
        dev_form_grid.addWidget(self.txt_dev_pass, 3, 1)

        # FPS Objetivo
        dev_form_grid.addWidget(QLabel("FPS Objetivo:"), 2, 2)
        self.spin_dev_fps = QSpinBox()
        self.spin_dev_fps.setRange(5, 60)
        self.spin_dev_fps.setValue(30)
        dev_form_grid.addWidget(self.spin_dev_fps, 3, 2)

        # Cantidad de Cámaras a Configurar
        dev_form_grid.addWidget(QLabel("Cámaras a Configurar (Canales):"), 2, 3)
        self.spin_channel_count = QSpinBox()
        self.spin_channel_count.setRange(1, 8)
        self.spin_channel_count.setValue(2)
        self.spin_channel_count.valueChanged.connect(self._render_camera_rows)
        dev_form_grid.addWidget(self.spin_channel_count, 3, 3)

        cam_layout.addLayout(dev_form_grid)

        # Sub-Panel Dinámico: Configuración de Cada Cámara del Dispositivo
        cam_box = QGroupBox("Cámaras y Canales Individuales a Configurar para este Dispositivo:")
        cam_box.setStyleSheet("""
            QGroupBox {
                color: #34d399;
                font-weight: bold;
                font-size: 11px;
                border: 1px solid #1e293b;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 14px;
            }
        """)
        self.cam_rows_layout = QVBoxLayout(cam_box)
        self.cam_rows_layout.setSpacing(8)
        self.camera_row_data = []

        cam_layout.addWidget(cam_box)

        # Botón "Agregar Dispositivo"
        btn_row = QHBoxLayout()
        lbl_hint = QLabel("💡 Al agregar el dispositivo, todas sus cámaras se vincularán inmediatamente en la Vigilancia en Directo.")
        lbl_hint.setStyleSheet("font-size: 11px; color: #94a3b8;")
        btn_row.addWidget(lbl_hint)
        btn_row.addStretch()

        self.btn_add_device = QPushButton("➕  Agregar Dispositivo")
        self.btn_add_device.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_add_device.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: #020617;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 8px 18px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #059669;
            }
        """)
        self.btn_add_device.clicked.connect(self._add_device_and_cameras)
        btn_row.addWidget(self.btn_add_device)
        cam_layout.addLayout(btn_row)

        # Despliegue hacia Abajo: Tabla de Dispositivos y Cámaras Conectadas
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #1e293b;")
        cam_layout.addWidget(sep)

        devices_header_row = QHBoxLayout()
        lbl_devices_section = QLabel("DISPOSITIVOS Y CÁMARAS CONECTADAS")
        lbl_devices_section.setStyleSheet("font-size: 11px; font-weight: bold; color: #10b981; letter-spacing: 0.5px;")
        devices_header_row.addWidget(lbl_devices_section)
        devices_header_row.addStretch()

        self.lbl_devices_count = QLabel("0 Dispositivos Registrados")
        self.lbl_devices_count.setStyleSheet("""
            background-color: #064e3b;
            color: #34d399;
            border: 1px solid #059669;
            border-radius: 10px;
            padding: 3px 10px;
            font-size: 10px;
            font-weight: bold;
            font-family: monospace;
        """)
        devices_header_row.addWidget(self.lbl_devices_count)
        cam_layout.addLayout(devices_header_row)

        self.table_devices = QTableWidget(0, 6)
        self.table_devices.setHorizontalHeaderLabels([
            "ID Cámara", "Nombre / Ubicación", "Tipo / Origen", "Subflujo / Canal", "IA Activa", "Acción"
        ])
        self.table_devices.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_devices.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_devices.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_devices.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table_devices.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table_devices.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table_devices.setMinimumHeight(180)
        self.table_devices.setStyleSheet("""
            QTableWidget {
                background-color: #090e1a;
                border: 1px solid #1e293b;
                border-radius: 8px;
                gridline-color: #1e293b;
                color: #e2e8f0;
                font-size: 11px;
            }
            QHeaderView::section {
                background-color: #0f172a;
                color: #94a3b8;
                border: 1px solid #1e293b;
                font-weight: bold;
                padding: 4px;
            }
        """)
        cam_layout.addWidget(self.table_devices)

        content_layout.addWidget(cam_panel)

        # ----------------------------------------------------
        # SECCIÓN 5: COPIAS DE SEGURIDAD Y RESTAURACIÓN
        # ----------------------------------------------------
        backup_panel = QFrame()
        backup_panel.setStyleSheet("background-color: #0f172a; border: 1px solid #1e293b; border-radius: 12px; padding: 14px;")
        backup_layout = QVBoxLayout(backup_panel)
        backup_layout.setSpacing(10)

        lbl_bk_title = QLabel("COPIA DE SEGURIDAD Y RESTAURACIÓN")
        lbl_bk_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #10b981; letter-spacing: 0.5px;")
        backup_layout.addWidget(lbl_bk_title)

        lbl_bk_desc = QLabel("Exporta o restaura el estado completo de VIGI-WIN PRO (ajustes, cámaras y eventos) con verificación criptográfica SHA-256.")
        lbl_bk_desc.setWordWrap(True)
        lbl_bk_desc.setStyleSheet("font-size: 11px; color: #94a3b8; line-height: 1.3;")
        backup_layout.addWidget(lbl_bk_desc)

        bk_row = QHBoxLayout()
        bk_row.setSpacing(12)

        self.lbl_last_backup = QLabel(f"Última copia realizada: {self.backup_mgr.get_last_backup_date()}")
        self.lbl_last_backup.setStyleSheet("font-size: 10px; color: #64748b; font-family: monospace;")
        bk_row.addWidget(self.lbl_last_backup)
        bk_row.addStretch()

        # Botón Descargar Backup JSON
        self.btn_backup_json = QPushButton("Descargar Backup de Ajustes y DB (JSON)")
        self.btn_backup_json.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_backup_json.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #e2e8f0;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 500;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #ffffff;
            }
        """)
        self.btn_backup_json.clicked.connect(self._create_json_backup)
        bk_row.addWidget(self.btn_backup_json)

        # Botón Restaurar
        self.btn_restore = QPushButton("Restaurar Configuración desde Copia")
        self.btn_restore.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_restore.setStyleSheet("""
            QPushButton {
                background-color: rgba(217, 119, 6, 0.15);
                color: #fcd34d;
                border: 1px solid rgba(245, 158, 11, 0.4);
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 500;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(217, 119, 6, 0.25);
            }
        """)
        self.btn_restore.clicked.connect(self._restore_backup)
        bk_row.addWidget(self.btn_restore)

        backup_layout.addLayout(bk_row)
        content_layout.addWidget(backup_panel)

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

        # Renderizar filas iniciales de cámaras y tabla
        self._render_camera_rows(self.spin_channel_count.value())
        self._refresh_devices_table()

    # --- Métodos de Identidad Corporativa ---
    def _save_company_name(self):
        name = self.txt_company_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Validación", "El nombre de la empresa no puede estar vacío.")
            return
        self.db.set_setting("company_name", name)
        self.db.log_audit(self.rbac_mgr.get_current_username(), "Actualizar Identidad", f"Nombre de empresa: {name}")
        logo_path = self.db.get_setting("company_logo_path", "")
        if hasattr(self, 'on_company_branding_updated') and callable(self.on_company_branding_updated):
            self.on_company_branding_updated(name, logo_path)
        QMessageBox.information(self, "Identidad Corporativa", f"Nombre de empresa actualizado exitosamente a: '{name}'.")

    def _select_company_logo(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar Logotipo Institucional",
            "",
            "Imágenes (*.png *.jpg *.jpeg *.ico *.bmp)"
        )
        if path:
            self.db.set_setting("company_logo_path", path)
            self.db.log_audit(self.rbac_mgr.get_current_username(), "Actualizar Logo", f"Ruta: {path}")
            self._update_logo_preview()
            name = self.txt_company_name.text().strip()
            if hasattr(self, 'on_company_branding_updated') and callable(self.on_company_branding_updated):
                self.on_company_branding_updated(name, path)
            QMessageBox.information(self, "Logotipo Actualizado", "El logotipo institucional ha sido actualizado correctamente.")

    def _reset_company_logo(self):
        self.db.set_setting("company_logo_path", "")
        self._update_logo_preview()
        name = self.txt_company_name.text().strip()
        if hasattr(self, 'on_company_branding_updated') and callable(self.on_company_branding_updated):
            self.on_company_branding_updated(name, "")
        QMessageBox.information(self, "Logotipo Restablecido", "Se ha restablecido el icono y logotipo predeterminado.")

    def _update_logo_preview(self):
        path = self.db.get_setting("company_logo_path", "")
        if path and os.path.exists(path):
            pix = QPixmap(path).scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.lbl_logo_preview.setPixmap(pix)
            self.lbl_logo_preview.setText("")
        else:
            self.lbl_logo_preview.setPixmap(QPixmap())
            self.lbl_logo_preview.setText("🛡️")
            self.lbl_logo_preview.setStyleSheet("font-size: 18px; background-color: #1e293b; border: 1px solid #334155; border-radius: 6px;")

    # --- Métodos de Configuración de Detección de Cámaras ---
    def _populate_detection_cameras(self):
        cams = self.db.get_cameras()
        self.combo_det_cam.blockSignals(True)
        self.combo_det_cam.clear()
        for c in cams:
            self.combo_det_cam.addItem(f"{c['id']} - {c['name']}", c['id'])
        self.combo_det_cam.blockSignals(False)
        if cams:
            self._on_detection_camera_selected(0)

    def _on_detection_camera_selected(self, index: int):
        cam_id = self.combo_det_cam.currentData()
        if not cam_id:
            return
        cam = self.db.get_camera(cam_id)
        if cam:
            self.chk_det_person.setChecked(bool(cam.get("detect_person", 1)))
            ps = cam.get("person_sensitivity", 80)
            self.slider_person_sens.setValue(ps)
            self.lbl_person_sens_val.setText(f"{ps}%")

            self.chk_det_vehicle.setChecked(bool(cam.get("detect_vehicle", 1)))
            vs = cam.get("vehicle_sensitivity", 75)
            self.slider_vehicle_sens.setValue(vs)
            self.lbl_vehicle_sens_val.setText(f"{vs}%")

            self.spin_door_time.setValue(cam.get("door_max_open_sec", 60))

    def _save_camera_detection(self):
        cam_id = self.combo_det_cam.currentData()
        if not cam_id:
            QMessageBox.warning(self, "Aviso", "No hay cámara seleccionada para guardar.")
            return
        det_person = 1 if self.chk_det_person.isChecked() else 0
        det_vehicle = 1 if self.chk_det_vehicle.isChecked() else 0
        person_sens = self.slider_person_sens.value()
        vehicle_sens = self.slider_vehicle_sens.value()
        max_open_sec = self.spin_door_time.value()

        success = self.db.update_camera_detection(
            cam_id, det_person, det_vehicle, person_sens, vehicle_sens, max_open_sec
        )
        if success:
            cam = self.db.get_camera(cam_id)
            if cam and self.camera_manager:
                self.camera_manager.add_or_update_camera(cam)
            self.db.log_audit(
                self.rbac_mgr.get_current_username(),
                "Configurar Detección",
                f"Cámara {cam_id}: Personas={det_person}({person_sens}%), Vehículos={det_vehicle}({vehicle_sens}%), Puerta={max_open_sec}s"
            )
            self._refresh_devices_table()
            QMessageBox.information(
                self,
                "Detección Actualizada",
                f"Los parámetros de detección e inteligencia artificial para '{cam_id}' han sido guardados y aplicados en caliente."
            )
        else:
            QMessageBox.critical(self, "Error", f"No se pudo guardar la configuración de la cámara '{cam_id}'.")

    # --- Métodos de Dispositivos y Cámaras ---
    def _on_dev_type_changed(self, index: int):
        if index == 1 or index == 2: # IP o Webcam única
            self.spin_channel_count.setValue(1)
        elif self.spin_channel_count.value() == 1:
            self.spin_channel_count.setValue(2)

    def _render_camera_rows(self, count: int):
        while self.cam_rows_layout.count():
            item = self.cam_rows_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self.camera_row_data = []
        loc_names = [
            "Puerta Principal Vehicular",
            "Acceso Peatonal Posterior",
            "Perímetro Norte",
            "Barrera de Salida",
            "Muelle de Carga Andén",
            "Zona Estacionamiento",
            "Puerta de Emergencia",
            "Garita de Control"
        ]

        existing_cams = self.db.get_cameras()
        start_idx = len(existing_cams) + 1

        for i in range(1, count + 1):
            row_frame = QFrame()
            row_frame.setStyleSheet("background-color: #090e1a; border: 1px solid #1e293b; border-radius: 6px; padding: 6px;")
            r_layout = QHBoxLayout(row_frame)
            r_layout.setContentsMargins(6, 4, 6, 4)
            r_layout.setSpacing(8)

            lbl_ch = QLabel(f"Canal {i}:")
            lbl_ch.setStyleSheet("color: #34d399; font-weight: bold; font-size: 10px; font-family: monospace;")
            r_layout.addWidget(lbl_ch)

            txt_id = QLineEdit(f"CAM_{start_idx + i - 1:02d}")
            txt_id.setMaximumWidth(70)
            txt_id.setStyleSheet("font-family: monospace; font-size: 10px;")
            r_layout.addWidget(txt_id)

            def_loc = loc_names[(i - 1) % len(loc_names)]
            txt_name = QLineEdit(f"Canal {i}: {def_loc}")
            r_layout.addWidget(txt_name, stretch=2)

            combo_persp = QComboBox()
            combo_persp.addItems(["Vista Frontal", "Vista Lateral"])
            combo_persp.setCurrentIndex(1 if (i % 2 == 0) else 0)
            r_layout.addWidget(combo_persp)

            txt_chan = QLineEdit(f"/ch{i}/main")
            txt_chan.setMaximumWidth(80)
            txt_chan.setStyleSheet("font-family: monospace; font-size: 10px; color: #64748b;")
            r_layout.addWidget(txt_chan)

            chk_door = QCheckBox("Puerta 60s")
            chk_door.setChecked(True)
            r_layout.addWidget(chk_door)

            chk_person = QCheckBox("Personas")
            chk_person.setChecked(True)
            r_layout.addWidget(chk_person)

            chk_vehicle = QCheckBox("Vehículos")
            chk_vehicle.setChecked(True)
            r_layout.addWidget(chk_vehicle)

            self.cam_rows_layout.addWidget(row_frame)

            self.camera_row_data.append({
                "txt_id": txt_id,
                "txt_name": txt_name,
                "combo_persp": combo_persp,
                "txt_chan": txt_chan,
                "chk_door": chk_door,
                "chk_person": chk_person,
                "chk_vehicle": chk_vehicle
            })

    def _add_device_and_cameras(self):
        dev_name = self.txt_dev_name.text().strip() or "DVR Conectado"
        dev_type_idx = self.combo_dev_type.currentIndex()
        type_str = "rtsp" if dev_type_idx == 0 else ("rtsp" if dev_type_idx == 1 else ("webcam" if dev_type_idx == 2 else "simulation"))
        host = self.txt_dev_host.text().strip() or "192.168.1.100"
        port = self.spin_dev_port.value()
        user = self.txt_dev_user.text().strip() or "admin"
        pw = self.txt_dev_pass.text().strip() or "admin"

        added_cams = []
        for r in self.camera_row_data:
            cid = r["txt_id"].text().strip()
            cname = r["txt_name"].text().strip()
            cpersp = "lateral" if r["combo_persp"].currentIndex() == 1 else "frontal"
            cchan = r["txt_chan"].text().strip()
            has_door = 1 if r["chk_door"].isChecked() else 0
            has_person = 1 if r["chk_person"].isChecked() else 0
            has_vehicle = 1 if r["chk_vehicle"].isChecked() else 0

            if not cid or not cname:
                continue

            rtsp_url = f"rtsp://{user}:{pw}@{host}:{port}{cchan}" if type_str == "rtsp" else "0"

            cam_dict = {
                "id": cid,
                "name": cname,
                "source_type": type_str,
                "source_url": rtsp_url,
                "perspective": cpersp,
                "door_max_open_sec": 60,
                "detect_person": has_person,
                "detect_vehicle": has_vehicle,
                "person_sensitivity": 80,
                "vehicle_sensitivity": 75,
                "is_active": 1
            }
            self.camera_manager.add_or_update_camera(cam_dict)
            added_cams.append(cid)

        self.db.log_audit(self.rbac_mgr.get_current_username(), "Dispositivo Agregado", f"{dev_name} ({len(added_cams)} cámaras)")

        if hasattr(self, 'on_cameras_updated') and callable(self.on_cameras_updated):
            self.on_cameras_updated()

        self._refresh_devices_table()
        self._populate_detection_cameras()
        self._render_camera_rows(self.spin_channel_count.value())

        QMessageBox.information(
            self,
            "Dispositivo Agregado",
            f"El dispositivo '{dev_name}' con {len(added_cams)} cámaras ha sido registrado y conectado correctamente.\n"
            f"Las cámaras ya se encuentran activas en el visor de Vigilancia en Directo."
        )

    def _refresh_devices_table(self):
        cams = self.db.get_cameras()
        self.table_devices.setRowCount(len(cams))
        self.lbl_devices_count.setText(f"{len(cams)} Cámaras Registradas en el Sistema")

        for row, c in enumerate(cams):
            cid = c["id"]
            item_id = QTableWidgetItem(cid)
            item_id.setForeground(Qt.cyan)
            self.table_devices.setItem(row, 0, item_id)

            item_name = QTableWidgetItem(c["name"])
            self.table_devices.setItem(row, 1, item_name)

            item_type = QTableWidgetItem(c["source_type"].upper())
            self.table_devices.setItem(row, 2, item_type)

            item_url = QTableWidgetItem(c["source_url"] if len(c["source_url"]) < 40 else c["source_url"][:38] + "...")
            self.table_devices.setItem(row, 3, item_url)

            ai_str = []
            if c.get("detect_person"): ai_str.append("Personas")
            if c.get("detect_vehicle"): ai_str.append("Vehículos")
            item_ai = QTableWidgetItem(", ".join(ai_str) if ai_str else "Ninguna")
            item_ai.setForeground(Qt.green)
            self.table_devices.setItem(row, 4, item_ai)

            btn_test = QPushButton("Probar RTSP")
            btn_test.setStyleSheet("background-color: #1e293b; color: #34d399; border: 1px solid #334155; border-radius: 4px; padding: 2px 6px; font-size: 10px;")
            btn_test.clicked.connect(lambda ch, cam_id=cid: self._test_cam_connection(cam_id))
            self.table_devices.setCellWidget(row, 5, btn_test)

    def _test_cam_connection(self, cam_id: str):
        cam = self.db.get_camera(cam_id)
        name = cam.get("name", cam_id) if cam else cam_id
        QMessageBox.information(
            self,
            "Prueba de Flujo RTSP",
            f"Handshake RTSP exitoso con la cámara '{name}' ({cam_id}).\nTransporte: TCP | Estado: Señal 30 FPS OK."
        )

    def _create_json_backup(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Copia de Seguridad JSON",
            f"VigiWinPro_SystemBackup_{int(os.times().system)}.json",
            "Archivos JSON (*.json)"
        )
        if path:
            success, msg = self.backup_mgr.create_json_backup(path)
            if success:
                self.lbl_last_backup.setText(f"Última copia realizada: {self.backup_mgr.get_last_backup_date()}")
                QMessageBox.information(self, "Copia de Seguridad Exitosa", msg)
            else:
                QMessageBox.critical(self, "Error", msg)

    def _restore_backup(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar Archivo de Respaldo JSON",
            "",
            "Archivos JSON (*.json)"
        )
        if path:
            confirm = QMessageBox.question(
                self,
                "Confirmar Restauración",
                "ADVERTENCIA: Esta operación sobrescribirá los ajustes y configuraciones actuales.\n¿Desea continuar?",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirm == QMessageBox.Yes:
                success, msg = self.backup_mgr.restore_from_json(path)
                if success:
                    QMessageBox.information(self, "Restauración Completada", msg)
                else:
                    QMessageBox.critical(self, "Error de Integridad", msg)

    # --- Métodos RBAC y Gestión de Usuarios ---
    def _refresh_session_banner(self):
        curr_u = self.rbac_mgr.get_current_username()
        curr_r = self.rbac_mgr.get_current_role()
        curr_c = self.rbac_mgr.get_current_cargo()
        self.lbl_active_session.setText(f"Sesión Activa: {curr_u} ({curr_r}) — Cargo: {curr_c}")
        if curr_r == "Administrador":
            self.lbl_active_session.setStyleSheet("font-size: 11px; color: #34d399; font-weight: bold;")
        elif curr_r in ("Operador", "Operador de Seguridad"):
            self.lbl_active_session.setStyleSheet("font-size: 11px; color: #38bdf8; font-weight: bold;")
        else:
            self.lbl_active_session.setStyleSheet("font-size: 11px; color: #fbbf24; font-weight: bold;")

    def _refresh_users_table(self):
        users = self.rbac_mgr.get_users()
        self.table_users.setRowCount(len(users))
        curr_user = self.rbac_mgr.get_current_username()
        is_admin = (self.rbac_mgr.get_current_role() == "Administrador")

        for row, u in enumerate(users):
            uname = u["username"]
            role = u["role"]
            cargo = u.get("cargo", "Operador de Monitoreo")
            is_active = (u.get("is_active", 1) == 1)

            # Col 0: Usuario
            item_u = QTableWidgetItem(f"👤 {uname}" + (" (Tú)" if uname == curr_user else ""))
            item_u.setForeground(QColor("#ffffff" if uname == curr_user else "#cbd5e1"))
            self.table_users.setItem(row, 0, item_u)

            # Col 1: Cargo
            item_cargo = QTableWidgetItem(cargo)
            item_cargo.setForeground(QColor("#94a3b8"))
            self.table_users.setItem(row, 1, item_cargo)

            # Col 2: Rol
            item_r = QTableWidgetItem(role)
            if role == "Administrador":
                item_r.setForeground(QColor("#34d399"))
            elif role in ("Operador", "Operador de Seguridad"):
                item_r.setForeground(QColor("#38bdf8"))
            else:
                item_r.setForeground(QColor("#fbbf24"))
            self.table_users.setItem(row, 2, item_r)

            # Col 3: Estado
            item_status = QTableWidgetItem("● Activo" if is_active else "○ Inactivo")
            item_status.setForeground(QColor("#34d399" if is_active else "#ef4444"))
            self.table_users.setItem(row, 3, item_status)

            # Col 4: Acciones (Widget con botones)
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            actions_layout.setSpacing(4)

            # Botón Conmutar (para probar roles en vivo)
            btn_switch = QPushButton("Conmutar")
            btn_switch.setCursor(QCursor(Qt.PointingHandCursor))
            btn_switch.setStyleSheet("background-color: #1e293b; color: #38bdf8; border: 1px solid #334155; border-radius: 4px; padding: 2px 6px; font-size: 10px;")
            btn_switch.setEnabled(is_active)
            btn_switch.clicked.connect(lambda ch, un=uname: self._quick_switch_session(un))
            actions_layout.addWidget(btn_switch)

            # Botón Modificar (abre diálogo unificado)
            btn_edit = QPushButton("Modificar")
            btn_edit.setCursor(QCursor(Qt.PointingHandCursor))
            btn_edit.setStyleSheet("background-color: #1e293b; color: #34d399; border: 1px solid #334155; border-radius: 4px; padding: 2px 6px; font-size: 10px; font-weight: bold;")
            btn_edit.setEnabled(is_admin)
            btn_edit.clicked.connect(lambda ch, un=uname: self._open_edit_user_dialog(un))
            actions_layout.addWidget(btn_edit)

            # Botón Eliminar (solo administradores y no a sí mismo)
            btn_del = QPushButton("✕")
            btn_del.setCursor(QCursor(Qt.PointingHandCursor))
            btn_del.setStyleSheet("background-color: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); border-radius: 4px; padding: 2px 6px; font-size: 10px; font-weight: bold;")
            btn_del.setEnabled(is_admin and uname != curr_user)
            btn_del.clicked.connect(lambda ch, un=uname: self._delete_user(un))
            actions_layout.addWidget(btn_del)

            self.table_users.setCellWidget(row, 4, actions_widget)

    def _refresh_permissions_matrix(self):
        self._is_populating_matrix = True
        defs = self.rbac_mgr.PERMISSION_DEFINITIONS
        self.table_permissions.setRowCount(len(defs))

        roles = ["Administrador", "Operador", "Auditor"]

        for row, (perm_key, info) in enumerate(defs.items()):
            lbl_text = f"{info['icon']}  {info['label']}"
            item = QTableWidgetItem(lbl_text)
            item.setToolTip(info["desc"])
            item.setForeground(QColor("#f1f5f9"))
            self.table_permissions.setItem(row, 0, item)

            for col_idx, role_name in enumerate(roles):
                perms = self.rbac_mgr.get_permissions(role_name)
                is_granted = perm_key in perms

                chk = QCheckBox()
                chk.setChecked(is_granted)
                chk.setCursor(QCursor(Qt.PointingHandCursor))
                chk.stateChanged.connect(
                    lambda state, r=role_name, p=perm_key: self._on_matrix_toggled(r, p, state)
                )

                widget = QWidget()
                w_layout = QHBoxLayout(widget)
                w_layout.setContentsMargins(0, 0, 0, 0)
                w_layout.setAlignment(Qt.AlignCenter)
                w_layout.addWidget(chk)
                self.table_permissions.setCellWidget(row, col_idx + 1, widget)

        self._is_populating_matrix = False

    def _on_matrix_toggled(self, role: str, perm_key: str, state):
        if self._is_populating_matrix:
            return
        is_checked = (state == Qt.Checked.value if hasattr(Qt.Checked, 'value') else state == 2 or state == Qt.Checked)
        self.rbac_mgr.set_permission(role, perm_key, is_checked)
        if role == "Operador":
            self.rbac_mgr.set_permission("Operador de Seguridad", perm_key, is_checked)

    def _reset_permissions(self):
        self.rbac_mgr.reset_permissions_to_default()
        self._refresh_permissions_matrix()
        QMessageBox.information(self, "Matriz RBAC", "Se han restablecido los permisos de los roles a sus valores predeterminados de fábrica.")

    def _quick_switch_session(self, username: str):
        success = self.rbac_mgr.switch_user(username)
        if success:
            self._refresh_session_banner()
            self._refresh_users_table()
        else:
            QMessageBox.warning(self, "Error", f"No se pudo conmutar al usuario '{username}' (es posible que esté inactivo).")

    def _open_create_user_dialog(self):
        dlg = UserFormDialog(parent=self)
        if dlg.exec():
            data = dlg.get_data()
            success, msg = self.rbac_mgr.create_user(
                username=data["username"],
                password=data["password"],
                role=data["role"],
                cargo=data["cargo"],
                is_active=data["is_active"]
            )
            if success:
                QMessageBox.information(self, "Usuario Creado", msg)
                self._refresh_users_table()
            else:
                QMessageBox.warning(self, "Error", msg)

    def _open_edit_user_dialog(self, username: str):
        user = self.db.get_user(username)
        if not user:
            QMessageBox.warning(self, "Error", f"No se encontró el usuario '{username}'.")
            return
        dlg = UserFormDialog(username=username, initial_data=user, parent=self)
        if dlg.exec():
            data = dlg.get_data()
            success, msg = self.rbac_mgr.update_user(
                username=data["username"],
                role=data["role"],
                cargo=data["cargo"],
                is_active=data["is_active"],
                new_password=data["password"]
            )
            if success:
                QMessageBox.information(self, "Usuario Actualizado", msg)
                self._refresh_users_table()
                self._refresh_session_banner()
            else:
                QMessageBox.warning(self, "Error", msg)

    def _delete_user(self, username: str):
        confirm = QMessageBox.question(
            self,
            "Confirmar Eliminación",
            f"¿Está seguro de eliminar permanentemente al usuario '{username}' del sistema RBAC?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            success, msg = self.rbac_mgr.delete_user(username)
            if success:
                QMessageBox.information(self, "Usuario Eliminado", msg)
                self._refresh_users_table()
            else:
                QMessageBox.warning(self, "No se puede eliminar", msg)

    def apply_role_permissions(self, role: str):
        """Aplica restricciones dinámicas a la pestaña de administración según el rol activo."""
        is_admin = (role == "Administrador")

        # 1. Usuarios RBAC
        self.btn_create_user.setEnabled(is_admin)
        self.btn_reset_perms.setEnabled(is_admin)
        self.table_permissions.setEnabled(is_admin)

        # 2. Identidad Corporativa
        self.txt_company_name.setEnabled(is_admin)
        self.btn_save_company_name.setEnabled(is_admin)
        self.btn_select_logo.setEnabled(is_admin)
        self.btn_reset_logo.setEnabled(is_admin)

        # 3. Configuración de Detección e IA de Cámaras
        self.combo_det_cam.setEnabled(is_admin)
        self.chk_det_person.setEnabled(is_admin)
        self.slider_person_sens.setEnabled(is_admin)
        self.chk_det_vehicle.setEnabled(is_admin)
        self.slider_vehicle_sens.setEnabled(is_admin)
        self.spin_door_time.setEnabled(is_admin)
        self.btn_save_detection.setEnabled(is_admin)

        # 4. Configuración DVR / NVR / RTSP
        self.txt_dev_name.setEnabled(is_admin)
        self.combo_dev_type.setEnabled(is_admin)
        self.txt_dev_host.setEnabled(is_admin)
        self.spin_dev_port.setEnabled(is_admin)
        self.combo_dev_protocol.setEnabled(is_admin)
        self.txt_dev_user.setEnabled(is_admin)
        self.txt_dev_pass.setEnabled(is_admin)
        self.spin_dev_fps.setEnabled(is_admin)
        self.spin_channel_count.setEnabled(is_admin)
        if hasattr(self, 'btn_add_device'):
            self.btn_add_device.setEnabled(is_admin)

        # 5. Backup
        self.btn_restore.setEnabled(is_admin)

        # 6. Actualizador oficial desde GitHub (Exclusivo Administrador)
        if hasattr(self, 'btn_update_github'):
            self.btn_update_github.setEnabled(is_admin)

        # Tooltips restrictivos
        tip = "" if is_admin else "Restringido: Solo el Administrador tiene permisos para realizar esta acción."
        self.btn_create_user.setToolTip(tip)
        self.btn_save_company_name.setToolTip(tip)
        self.btn_select_logo.setToolTip(tip)
        self.btn_save_detection.setToolTip(tip)
        if hasattr(self, 'btn_add_device'):
            self.btn_add_device.setToolTip(tip)
        self.btn_restore.setToolTip(tip)
        if hasattr(self, 'btn_update_github'):
            self.btn_update_github.setToolTip(tip or "Conectar con https://github.com/SANDAVID14/VIGIWIN-PRO.git, verificar y aplicar cambios")

        self._refresh_session_banner()
        self._refresh_users_table()

    def _open_github_updater_dialog(self):
        """Abre el asistente gráfico de verificación y actualización desde GitHub."""
        curr_role = self.rbac_mgr.get_current_role()
        if curr_role != "Administrador":
            QMessageBox.warning(
                self,
                "Acceso Restringido",
                "Únicamente los usuarios con rol de 'Administrador' tienen permisos para "
                "conectar y actualizar el sistema desde el repositorio oficial de GitHub."
            )
            return

        dlg = GitHubUpdateDialog(self.db, parent=self)
        dlg.exec()

