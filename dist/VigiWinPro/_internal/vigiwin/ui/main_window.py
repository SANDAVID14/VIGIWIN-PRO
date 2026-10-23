"""
VIGI-WIN PRO - Ventana Principal de la Aplicación
Replica fielmente la arquitectura visual, interfaz, colores y navegación de 'Backend vigiwin.html'.
Integra los 5 módulos funcionales, el orquestador multi-cámara y el sistema de alertas flotante topmost.
"""
import os
from datetime import datetime
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QStackedWidget, QFrame, QApplication,
    QComboBox, QMessageBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCursor, QPixmap

from vigiwin.core.database import DatabaseManager
from vigiwin.core.audio import AudioManager
from vigiwin.core.rbac import RBACManager
from vigiwin.vision.camera_manager import CameraManager
from vigiwin.ui.styles import DARK_THEME_QSS
from vigiwin.ui.alert_overlay import CentralizedAlertOverlay
from vigiwin.ui.door_dialog import DoorClosedDialog

from vigiwin.ui.surveillance_tab import SurveillanceTab
from vigiwin.ui.history_tab import HistoryTab
from vigiwin.ui.admin_tab import AdminTab
from vigiwin.ui.code_tab import CodeTab
from vigiwin.ui.tests_tab import TestsTab

class VigiWinMainWindow(QMainWindow):
    def __init__(self, rbac_manager=None):
        super().__init__()
        self.setWindowTitle("VIGI-WIN PRO v1.0 - Sistema Inteligente de Vigilancia de Puertas, Personas y Vehículos")
        self.resize(1200, 780)
        self.setMinimumSize(920, 580)

        # Aplicar el tema gráfico Slate 950 + Emerald 500
        self.setStyleSheet(DARK_THEME_QSS)

        # 1. Inicializar Core y Servicios
        self.db = DatabaseManager()
        self.audio = AudioManager()
        self.rbac_mgr = rbac_manager or RBACManager(self.db)
        self.camera_manager = CameraManager(self.db)

        # Conectar callback de cambio de usuario RBAC
        self.rbac_mgr.on_user_changed = self._on_user_session_changed

        # 2. Inicializar Sistema Centralizado de Alertas Flotantes (Topmost abajo a la derecha)
        self.alert_overlay = CentralizedAlertOverlay(self.db, self.audio)
        self.alert_overlay.on_open_surveillance_callback = self._switch_to_surveillance


        # Conectar Callbacks de Visión Artificial al Sistema de Alertas
        self.camera_manager.on_door_alarm_callback = self._on_door_alarm
        self.camera_manager.on_door_closed_callback = self._on_door_closed
        self.camera_manager.on_person_alert_callback = self._on_person_alert
        self.camera_manager.on_vehicle_alert_callback = self._on_vehicle_alert
        self.camera_manager.on_signal_lost_callback = self._on_signal_lost

        # 3. Construir Interfaz de Usuario
        self.init_ui()

        # Iniciar cámara activa en hilo de captura
        self.camera_manager.start_active()

        # Reloj digital en vivo
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start(1000)
        self._update_clock()

    def init_ui(self):
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        main_vbox = QVBoxLayout(central_widget)
        main_vbox.setContentsMargins(0, 0, 0, 0)
        main_vbox.setSpacing(0)

        # ----------------------------------------------------
        # TOP BAR (Encabezado Superior)
        # ----------------------------------------------------
        top_header = QFrame()
        top_header.setObjectName("topHeader")
        header_layout = QHBoxLayout(top_header)
        header_layout.setContentsMargins(16, 0, 16, 0)
        header_layout.setSpacing(12)

        # Logotipo y Títulos
        logo_box = QHBoxLayout()
        self.logo_icon = QLabel("🛡️")
        self.logo_icon.setStyleSheet("font-size: 20px;")
        logo_box.addWidget(self.logo_icon)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_row = QHBoxLayout()
        self.lbl_app_name = QLabel("VIGI-WIN PRO")
        self.lbl_app_name.setStyleSheet("font-weight: bold; font-size: 13px; color: #ffffff; letter-spacing: 0.5px;")
        title_row.addWidget(self.lbl_app_name)

        lbl_badge_win = QLabel("v1.0 Windows Edition")
        lbl_badge_win.setStyleSheet("background-color: #064e3b; color: #34d399; border: 1px solid #059669; border-radius: 4px; padding: 2px 6px; font-size: 9px; font-weight: bold;")
        title_row.addWidget(lbl_badge_win)
        title_row.addStretch()
        title_col.addLayout(title_row)

        lbl_subtitle = QLabel("Sistema Inteligente de Vigilancia de Puertas, Personas y Vehículos")
        lbl_subtitle.setStyleSheet("font-size: 10px; color: #94a3b8;")
        title_col.addWidget(lbl_subtitle)
        logo_box.addLayout(title_col)
        header_layout.addLayout(logo_box)

        header_layout.addStretch()

        # Badge de Estado del Sistema
        badge_status = QLabel("● SISTEMA ACTIVO | Windows 10/11 OK")
        badge_status.setStyleSheet("background-color: rgba(6, 78, 59, 0.6); color: #34d399; border: 1px solid #059669; border-radius: 12px; padding: 4px 12px; font-size: 11px; font-family: monospace; font-weight: bold;")
        header_layout.addWidget(badge_status)

        # Reloj Digital
        self.lbl_clock = QLabel("00:00:00")
        self.lbl_clock.setStyleSheet("color: #94a3b8; font-family: monospace; font-size: 11px; margin-left: 6px; margin-right: 6px;")
        header_layout.addWidget(self.lbl_clock)

        # Badge de Sesión RBAC Activa
        self.lbl_user_badge = QLabel("👤 admin (Administrador)")
        self.lbl_user_badge.setStyleSheet("""
            background-color: rgba(16, 185, 129, 0.15);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.4);
            border-radius: 12px;
            padding: 4px 10px;
            font-size: 11px;
            font-weight: bold;
        """)
        header_layout.addWidget(self.lbl_user_badge)

        # Botón Cambiar de Usuario con Autenticación
        self.btn_switch_user = QPushButton("🔄 Cambiar Usuario")
        self.btn_switch_user.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_switch_user.setToolTip("Abrir ventana de autenticación para cambiar de usuario sin salir del sistema")
        self.btn_switch_user.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #34d399;
                border: 1px solid rgba(16, 185, 129, 0.4);
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(16, 185, 129, 0.2);
                border: 1px solid #10b981;
                color: #ffffff;
            }
        """)
        self.btn_switch_user.clicked.connect(self._open_switch_user_dialog)
        header_layout.addWidget(self.btn_switch_user)

        # Selector Rápido de Sesión en Header
        self.combo_header_users = QComboBox()
        self.combo_header_users.setToolTip("Conmutar sesión activa rápidamente")
        self.combo_header_users.setStyleSheet("""
            QComboBox {
                background-color: #1e293b;
                color: #e2e8f0;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 11px;
            }
        """)
        self.combo_header_users.currentIndexChanged.connect(self._on_header_user_selected)
        header_layout.addWidget(self.combo_header_users)

        # Botón Diagnóstico 24P
        self.btn_diag = QPushButton("Diagnóstico 24P")
        self.btn_diag.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_diag.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #e2e8f0;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #334155;
            }
        """)
        self.btn_diag.clicked.connect(self._open_diagnostics)
        header_layout.addWidget(self.btn_diag)

        # Botón Descargar Paquete .exe
        self.btn_build = QPushButton("Descargar Paquete .EXE")
        self.btn_build.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_build.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: #020617;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #059669;
            }
        """)
        self.btn_build.clicked.connect(lambda: self.switch_tab(3))
        header_layout.addWidget(self.btn_build)

        main_vbox.addWidget(top_header)

        # ----------------------------------------------------
        # BODY: Sidebar Izquierda + StackedWidget de Pestañas
        # ----------------------------------------------------
        body_layout = QHBoxLayout()
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # Barra Lateral (Sidebar)
        sidebar = QFrame()
        sidebar.setObjectName("sidebarPanel")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 14, 10, 14)
        sidebar_layout.setSpacing(6)

        lbl_menu = QLabel("MÓDULOS DEL SISTEMA")
        lbl_menu.setStyleSheet("color: #64748b; font-size: 9px; font-weight: bold; letter-spacing: 0.5px; padding-left: 8px; margin-bottom: 4px;")
        sidebar_layout.addWidget(lbl_menu)

        # Botones de las 5 Pestañas
        self.nav_buttons = []

        self.btn_nav_surv = QPushButton("📹  Vigilancia en Directo")
        self.btn_nav_surv.setProperty("class", "nav-button nav-button-active")
        self.btn_nav_surv.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_nav_surv.clicked.connect(lambda: self.switch_tab(0))
        sidebar_layout.addWidget(self.btn_nav_surv)
        self.nav_buttons.append(self.btn_nav_surv)

        self.btn_nav_logs = QPushButton("📋  Historial & Alertas")
        self.btn_nav_logs.setProperty("class", "nav-button")
        self.btn_nav_logs.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_nav_logs.clicked.connect(lambda: self.switch_tab(1))
        sidebar_layout.addWidget(self.btn_nav_logs)
        self.nav_buttons.append(self.btn_nav_logs)

        self.btn_nav_admin = QPushButton("🛡️  Administración & RBAC")
        self.btn_nav_admin.setProperty("class", "nav-button")
        self.btn_nav_admin.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_nav_admin.clicked.connect(lambda: self.switch_tab(2))
        sidebar_layout.addWidget(self.btn_nav_admin)
        self.nav_buttons.append(self.btn_nav_admin)

        self.btn_nav_code = QPushButton("💻  Gestor de Código & Build")
        self.btn_nav_code.setProperty("class", "nav-button")
        self.btn_nav_code.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_nav_code.clicked.connect(lambda: self.switch_tab(3))
        sidebar_layout.addWidget(self.btn_nav_code)
        self.nav_buttons.append(self.btn_nav_code)

        self.btn_nav_tests = QPushButton("🧪  Suite de Tests (24P)")
        self.btn_nav_tests.setProperty("class", "nav-button")
        self.btn_nav_tests.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_nav_tests.clicked.connect(lambda: self.switch_tab(4))
        sidebar_layout.addWidget(self.btn_nav_tests)
        self.nav_buttons.append(self.btn_nav_tests)

        sidebar_layout.addStretch()

        # Pie de la Barra Lateral: Estado SQLite
        db_footer = QFrame()
        db_footer.setStyleSheet("background-color: #060b17; border-top: 1px solid #1e293b; border-radius: 6px; padding: 8px;")
        db_foot_layout = QVBoxLayout(db_footer)
        db_foot_layout.setSpacing(3)
        lbl_db_stat = QLabel("SQLite: Conectado")
        lbl_db_stat.setStyleSheet("color: #34d399; font-size: 10px; font-weight: bold;")
        db_foot_layout.addWidget(lbl_db_stat)

        lbl_db_path = QLabel("~/.vigiwinpro/vigiwin.db")
        lbl_db_path.setStyleSheet("color: #64748b; font-size: 9px; font-family: monospace;")
        db_foot_layout.addWidget(lbl_db_path)
        sidebar_layout.addWidget(db_footer)

        body_layout.addWidget(sidebar)

        # Stack de Pestañas
        self.tab_stack = QStackedWidget()

        self.tab_surveillance = SurveillanceTab(self.camera_manager, self.db, self.audio)
        self.tab_surveillance.alert_requested.connect(self._on_simulated_alert)
        self.tab_stack.addWidget(self.tab_surveillance) # Index 0

        self.tab_history = HistoryTab(self.db)
        self.tab_stack.addWidget(self.tab_history)      # Index 1

        self.tab_admin = AdminTab(self.db, self.camera_manager, self.rbac_mgr)
        self.tab_admin.on_cameras_updated = self.tab_surveillance._refresh_camera_list
        self.tab_admin.on_company_branding_updated = self.update_company_branding
        self.tab_stack.addWidget(self.tab_admin)          # Index 2

        self.tab_code = CodeTab()
        self.tab_stack.addWidget(self.tab_code)          # Index 3

        self.tab_tests = TestsTab(self.db, self.camera_manager)
        self.tab_stack.addWidget(self.tab_tests)        # Index 4

        body_layout.addWidget(self.tab_stack)
        main_vbox.addLayout(body_layout)

        # Aplicar identidad corporativa inicial
        initial_company = self.db.get_setting("company_name", "VIGI-WIN PRO")
        initial_logo = self.db.get_setting("company_logo_path", "")
        self.update_company_branding(initial_company, initial_logo)

        # Inicializar selector de usuarios y aplicar restricciones iniciales de sesión
        self._populate_header_users()
        self._on_user_session_changed(self.rbac_mgr.current_user or {})

    def switch_tab(self, index: int):
        self.tab_stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            if i == index:
                btn.setProperty("class", "nav-button nav-button-active")
            else:
                btn.setProperty("class", "nav-button")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        if index == 1:
            self.tab_history.refresh_table()

    def _open_diagnostics(self):
        self.switch_tab(4)
        self.tab_tests.run_full_diagnostics()

    def _switch_to_surveillance(self):
        self.switch_tab(0)
        self.activateWindow()

    def _update_clock(self):
        self.lbl_clock.setText(datetime.now().strftime("%H:%M:%S"))

    # --- Callbacks de Eventos de Visión Artificial ---
    def _on_door_alarm(self, door_result):
        cid = door_result.get("camera_id", "CAM_01")
        elapsed = door_result.get("elapsed_seconds", 60.0)
        msg = f"¡Atención! La puerta en {cid} permanece abierta por más de {int(elapsed)} segundos consecutivos."
        snap_path = self.camera_manager.save_snapshot(cid, "Puerta_Alarma")
        eid = self.db.log_event(cid, "Alerta Puerta", msg, "Alta", door_result, snapshot_path=snap_path)
        self.alert_overlay.show_alert(
            title="ALERTA CRÍTICA: PUERTA ABIERTA",
            message=msg,
            camera=cid,
            priority="Alta",
            db_event_id=eid
        )
        self.tab_history.refresh_table()

    def _on_door_closed(self, door_result):
        cid = door_result.get("camera_id", "CAM_01")
        duration = door_result.get("total_open_duration", 0.0)
        msg = f"Puerta cerrada correctamente. Tiempo total de apertura: {duration}s."
        snap_path = self.camera_manager.save_snapshot(cid, "Puerta_Cerrada")
        eid = self.db.log_event(cid, "Cierre Puerta", msg, "Baja", door_result, snapshot_path=snap_path)
        self.audio.play_door_closed_notice()
        self.tab_history.refresh_table()

        # Mostrar cuadro de diálogo con botón «Aceptar» obligatorio (Requisito Sección 3.14)
        def _on_confirm(cam, dur):
            self.db.confirm_event(eid, "Operador")
            self.db.log_audit("Operador", "Aviso de Cierre Aceptado", f"Cámara: {cam}")
            self.tab_history.refresh_table()

        dlg = DoorClosedDialog(cid, duration, on_confirm_callback=_on_confirm, parent=self)
        dlg.show()

    def _on_person_alert(self, person_data):
        cid = person_data.get("camera_id", "CAM_01")
        msg = person_data.get("message", "Persona detectada")
        snap_path = self.camera_manager.save_snapshot(cid, "Persona")
        eid = self.db.log_event(cid, "Persona", msg, "Media", person_data, snapshot_path=snap_path)
        self.alert_overlay.show_alert(
            title="DETECCIÓN DE PERSONA",
            message=msg,
            camera=cid,
            priority="Media",
            db_event_id=eid,
            auto_dismiss_sec=12
        )
        self.tab_history.refresh_table()

    def _on_vehicle_alert(self, vehicle_data):
        cid = vehicle_data.get("camera_id", "CAM_01")
        msg = vehicle_data.get("message", "Vehículo detectado")
        snap_path = self.camera_manager.save_snapshot(cid, "Vehículo")
        eid = self.db.log_event(cid, "Vehículo", msg, "Media", vehicle_data, snapshot_path=snap_path)
        self.alert_overlay.show_alert(
            title="DETECCIÓN DE VEHÍCULO",
            message=msg,
            camera=cid,
            priority="Media",
            db_event_id=eid,
            auto_dismiss_sec=12
        )
        self.tab_history.refresh_table()

    def _on_signal_lost(self, camera_id: str):
        msg = f"Pérdida de señal en {camera_id}. Intentando reconexión automática..."
        snap_path = self.camera_manager.save_snapshot(camera_id, "Fallo_Camara")
        eid = self.db.log_event(camera_id, "Fallo Cámara", msg, "Alta", snapshot_path=snap_path)
        self.alert_overlay.show_alert(
            title="FALLO DE CÁMARA / PÉRDIDA DE SEÑAL",
            message=msg,
            camera=camera_id,
            priority="Alta",
            db_event_id=eid
        )
        self.tab_history.refresh_table()

    def _on_simulated_alert(self, title, msg, cam, prio):
        snap_path = self.camera_manager.save_snapshot(cam, title)
        eid = self.db.log_event(cam, title, msg, prio, snapshot_path=snap_path)
        self.alert_overlay.show_alert(title, msg, camera=cam, priority=prio, db_event_id=eid)
        self.tab_history.refresh_table()

    def closeEvent(self, event):
        # Detener hilos de captura de vídeo de forma limpia
        self.camera_manager.stop_all()
        self.alert_overlay.close()
        event.accept()

    # --- Gestión y Restricciones Dinámicas de Sesión RBAC ---
    def _populate_header_users(self):
        self.combo_header_users.blockSignals(True)
        self.combo_header_users.clear()
        users = self.rbac_mgr.get_users()
        curr_user = self.rbac_mgr.get_current_username()
        curr_idx = 0
        for idx, u in enumerate(users):
            self.combo_header_users.addItem(f"{u['username']} ({u['role']})", u['username'])
            if u['username'] == curr_user:
                curr_idx = idx
        self.combo_header_users.setCurrentIndex(curr_idx)
        self.combo_header_users.blockSignals(False)

    def _open_switch_user_dialog(self):
        """Abre la ventana de login para conmutar de usuario sin salir de la aplicación."""
        from vigiwin.ui.login_dialog import LoginDialog
        dlg = LoginDialog(self.rbac_mgr, is_switch_user=True, parent=self)
        if dlg.exec():
            new_user = self.rbac_mgr.get_current_username()
            new_role = self.rbac_mgr.get_current_role()
            QMessageBox.information(
                self,
                "Sesión Actualizada",
                f"Ha iniciado sesión exitosamente como:\n• Usuario: {new_user}\n• Rol: {new_role}\n\nLos controles y permisos del sistema han sido actualizados."
            )

    def _on_header_user_selected(self, index):
        username = self.combo_header_users.currentData()
        if username and username != self.rbac_mgr.get_current_username():
            self.rbac_mgr.switch_user(username)

    def _on_user_session_changed(self, user_info):
        role = user_info.get("role", "Invitado")
        username = user_info.get("username", "Desconocido")

        # 1. Actualizar Badge y Selector del Header
        self.lbl_user_badge.setText(f"👤 {username} ({role})")
        if role == "Administrador":
            self.lbl_user_badge.setStyleSheet("""
                background-color: rgba(16, 185, 129, 0.15);
                color: #34d399;
                border: 1px solid rgba(16, 185, 129, 0.4);
                border-radius: 12px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: bold;
            """)
        elif role in ("Operador", "Operador de Seguridad"):
            self.lbl_user_badge.setStyleSheet("""
                background-color: rgba(56, 189, 248, 0.15);
                color: #38bdf8;
                border: 1px solid rgba(56, 189, 248, 0.4);
                border-radius: 12px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: bold;
            """)
        else: # Auditor
            self.lbl_user_badge.setStyleSheet("""
                background-color: rgba(245, 158, 11, 0.15);
                color: #fbbf24;
                border: 1px solid rgba(245, 158, 11, 0.4);
                border-radius: 12px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: bold;
            """)

        self._populate_header_users()

        # 2. Aplicar restricciones de interfaz (Módulos bloqueados)
        is_admin = (role == "Administrador")
        self.btn_nav_code.setEnabled(is_admin)
        self.btn_nav_tests.setEnabled(is_admin)
        self.btn_diag.setEnabled(is_admin)
        self.btn_build.setEnabled(is_admin)

        if not is_admin:
            self.btn_nav_code.setText("💻  Gestor de Código (🔒)")
            self.btn_nav_code.setToolTip("Restringido: Requiere rol Administrador")
            self.btn_nav_tests.setText("🧪  Suite de Tests (🔒)")
            self.btn_nav_tests.setToolTip("Restringido: Requiere rol Administrador")
            self.btn_diag.setToolTip("Restringido: Solo Administrador")
            self.btn_build.setToolTip("Restringido: Solo Administrador")
        else:
            self.btn_nav_code.setText("💻  Gestor de Código & Build")
            self.btn_nav_code.setToolTip("")
            self.btn_nav_tests.setText("🧪  Suite de Tests (24P)")
            self.btn_nav_tests.setToolTip("")
            self.btn_diag.setToolTip("")
            self.btn_build.setToolTip("")

        # 3. Propagar a las pestañas hijas
        if hasattr(self, 'tab_surveillance'):
            self.tab_surveillance.apply_role_permissions(role)
        if hasattr(self, 'tab_history'):
            self.tab_history.apply_role_permissions(role)
        if hasattr(self, 'tab_admin'):
            self.tab_admin.apply_role_permissions(role)

        # 4. Si el usuario estaba en una pestaña restringida, regresar a la pestaña 0
        if not is_admin and self.tab_stack.currentIndex() in [3, 4]:
            self.switch_tab(0)
            QMessageBox.information(
                self,
                "Acceso Restringido",
                f"El rol actual ({role}) no tiene autorización para acceder al módulo seleccionado.\nSe ha redirigido a Vigilancia en Directo."
            )

    def update_company_branding(self, company_name: str, logo_path: str = ""):
        """Actualiza el nombre de la empresa y el logotipo en toda la aplicación."""
        if not company_name:
            company_name = "VigiWin Pro - Sistema Inteligente de Vigilancia"
        self.setWindowTitle(f"{company_name} - Windows 10/11 x64")
        self.lbl_app_name.setText(company_name)
        if logo_path and os.path.exists(logo_path):
            try:
                pix = QPixmap(logo_path).scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.logo_icon.setPixmap(pix)
                self.logo_icon.setText("")
            except Exception:
                self.logo_icon.setPixmap(QPixmap())
                self.logo_icon.setText("🛡️")
        else:
            self.logo_icon.setPixmap(QPixmap())
            self.logo_icon.setText("🛡️")


