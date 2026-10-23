"""
VIGI-WIN PRO - Diálogo de Inicio de Sesión y Conmutación de Usuario (RBAC)
Diseño oscuro Slate 950 + Emerald 500 acorde a 'Backend vigiwin.html'.
Permite autenticación segura inicial y cambio de usuario en caliente dentro de la aplicación.
"""
import os
from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QSizePolicy, QMessageBox, QApplication
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor, QIcon, QAction

from vigiwin.core.rbac import RBACManager


class LoginDialog(QDialog):
    """Ventana modal de autenticación segura con usuario y contraseña."""
    def __init__(self, rbac_manager: RBACManager, is_switch_user: bool = False, parent=None):
        super().__init__(parent)
        self.rbac_mgr = rbac_manager
        self.is_switch_user = is_switch_user
        self.authenticated_user = None

        self.setWindowTitle(
            "VIGI-WIN PRO - Cambiar de Usuario" if is_switch_user else "VIGI-WIN PRO - Iniciar Sesión"
        )
        # Adaptabilidad automática a la resolución de pantalla
        screen = QApplication.primaryScreen()
        avail_h = screen.availableGeometry().height() if screen else 768
        target_h = min(530, max(440, int(avail_h * 0.85)))
        self.resize(440, target_h)
        self.setMinimumSize(380, 420)
        self.setModal(True)

        # Icono de ventana
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.setStyleSheet("""
            QDialog {
                background-color: #0b1120;
                color: #f8fafc;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 28, 28, 24)
        main_layout.setSpacing(14)

        # ----------------------------------------------------
        # ENCABEZADO: Icono + Título + Subtítulo
        # ----------------------------------------------------
        header_box = QVBoxLayout()
        header_box.setAlignment(Qt.AlignCenter)
        header_box.setSpacing(4)

        lbl_icon = QLabel("🛡️")
        lbl_icon.setAlignment(Qt.AlignCenter)
        lbl_icon.setStyleSheet("font-size: 38px; margin-bottom: 2px;")
        header_box.addWidget(lbl_icon)

        lbl_title = QLabel("VIGI-WIN PRO")
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff; letter-spacing: 0.5px;")
        header_box.addWidget(lbl_title)

        if self.is_switch_user:
            curr_user = self.rbac_mgr.get_current_username()
            curr_role = self.rbac_mgr.get_current_role()
            lbl_sub = QLabel(f"Cambio de Sesión en Caliente\n(Sesión actual: {curr_user} — {curr_role})")
            lbl_sub.setAlignment(Qt.AlignCenter)
            lbl_sub.setStyleSheet("font-size: 11px; color: #34d399; font-weight: 500;")
            header_box.addWidget(lbl_sub)
        else:
            lbl_sub = QLabel("Control de Acceso Seguro y Vigilancia de Accesos")
            lbl_sub.setAlignment(Qt.AlignCenter)
            lbl_sub.setStyleSheet("font-size: 11px; color: #94a3b8;")
            header_box.addWidget(lbl_sub)

        main_layout.addLayout(header_box)

        # Línea divisoria sutil
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #1e293b; margin: 4px 0;")
        main_layout.addWidget(sep)

        # ----------------------------------------------------
        # FORMULARIO DE CREDENCIALES
        # ----------------------------------------------------
        form_layout = QVBoxLayout()
        form_layout.setSpacing(10)

        # Campo Usuario
        lbl_user = QLabel("Nombre de Usuario:")
        lbl_user.setStyleSheet("font-size: 11px; font-weight: 600; color: #cbd5e1;")
        form_layout.addWidget(lbl_user)

        self.txt_username = QLineEdit()
        self.txt_username.setPlaceholderText("Ej: admin, operador, auditor...")
        self.txt_username.setStyleSheet("""
            QLineEdit {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #1e293b;
                border-radius: 8px;
                padding: 10px 12px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #10b981;
                background-color: #020617;
            }
        """)
        form_layout.addWidget(self.txt_username)

        # Campo Contraseña
        lbl_pass = QLabel("Contraseña:")
        lbl_pass.setStyleSheet("font-size: 11px; font-weight: 600; color: #cbd5e1; margin-top: 4px;")
        form_layout.addWidget(lbl_pass)

        pass_box = QHBoxLayout()
        pass_box.setSpacing(6)

        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.Password)
        self.txt_password.setPlaceholderText("Ingrese su contraseña...")
        self.txt_password.setStyleSheet("""
            QLineEdit {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #1e293b;
                border-radius: 8px;
                padding: 10px 12px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #10b981;
                background-color: #020617;
            }
        """)
        self.txt_password.returnPressed.connect(self._do_login)
        pass_box.addWidget(self.txt_password)

        # Botón Mostrar/Ocultar Contraseña
        self.btn_toggle_eye = QPushButton("👁️")
        self.btn_toggle_eye.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_toggle_eye.setToolTip("Mostrar/Ocultar contraseña")
        self.btn_toggle_eye.setFixedSize(38, 38)
        self.btn_toggle_eye.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #94a3b8;
                border: 1px solid #334155;
                border-radius: 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #f8fafc;
            }
        """)
        self.btn_toggle_eye.clicked.connect(self._toggle_password_visibility)
        pass_box.addWidget(self.btn_toggle_eye)

        form_layout.addLayout(pass_box)

        # Etiqueta de Error (roja)
        self.lbl_error = QLabel("")
        self.lbl_error.setAlignment(Qt.AlignCenter)
        self.lbl_error.setStyleSheet("color: #f87171; font-size: 11px; font-weight: bold; min-height: 18px;")
        form_layout.addWidget(self.lbl_error)

        main_layout.addLayout(form_layout)

        # ----------------------------------------------------
        # BOTONES RÁPIDOS DE PRUEBA / ROLES POR DEFECTO
        # ----------------------------------------------------
        chips_frame = QFrame()
        chips_frame.setStyleSheet("""
            QFrame {
                background-color: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 8px;
                padding: 6px;
            }
        """)
        chips_layout = QVBoxLayout(chips_frame)
        chips_layout.setContentsMargins(8, 6, 8, 6)
        chips_layout.setSpacing(4)

        lbl_chips_title = QLabel("Acceso rápido con cuentas predeterminadas:")
        lbl_chips_title.setStyleSheet("font-size: 10px; color: #64748b; font-weight: 500;")
        chips_layout.addWidget(lbl_chips_title)

        chips_row = QHBoxLayout()
        chips_row.setSpacing(6)

        accounts = [
            ("👑 Admin", "admin", "admin123"),
            ("🛡️ Operador", "operador", "operador123"),
            ("📋 Auditor", "auditor", "auditor123")
        ]

        for label, u, p in accounts:
            btn_chip = QPushButton(label)
            btn_chip.setCursor(QCursor(Qt.PointingHandCursor))
            btn_chip.setStyleSheet("""
                QPushButton {
                    background-color: #1e293b;
                    color: #cbd5e1;
                    border: 1px solid #334155;
                    border-radius: 6px;
                    padding: 4px 8px;
                    font-size: 10px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #334155;
                    color: #10b981;
                    border: 1px solid #10b981;
                }
            """)
            btn_chip.clicked.connect(lambda _, user=u, pwd=p: self._fill_credentials(user, pwd))
            chips_row.addWidget(btn_chip)

        chips_layout.addLayout(chips_row)
        main_layout.addWidget(chips_frame)

        # ----------------------------------------------------
        # BOTONES DE ACCIÓN: Iniciar Sesión / Cancelar
        # ----------------------------------------------------
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_cancel = QPushButton("Cancelar" if self.is_switch_user else "Salir")
        self.btn_cancel.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #cbd5e1;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 10px 18px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #ffffff;
            }
        """)
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_login = QPushButton("Cambiar Usuario" if self.is_switch_user else "Iniciar Sesión")
        self.btn_login.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_login.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: #020617;
                font-weight: bold;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #059669;
            }
            QPushButton:pressed {
                background-color: #047857;
            }
        """)
        self.btn_login.clicked.connect(self._do_login)
        btn_layout.addWidget(self.btn_login)

        main_layout.addLayout(btn_layout)

        # Foco inicial
        self.txt_username.setFocus()

    def _fill_credentials(self, u: str, p: str):
        self.txt_username.setText(u)
        self.txt_password.setText(p)
        self.lbl_error.setText("")
        self.txt_password.setFocus()

    def _toggle_password_visibility(self):
        if self.txt_password.echoMode() == QLineEdit.Password:
            self.txt_password.setEchoMode(QLineEdit.Normal)
            self.btn_toggle_eye.setText("🙈")
        else:
            self.txt_password.setEchoMode(QLineEdit.Password)
            self.btn_toggle_eye.setText("👁️")

    def _do_login(self):
        username = self.txt_username.text().strip()
        password = self.txt_password.text()

        if not username:
            self.lbl_error.setText("⚠️ Por favor ingrese su nombre de usuario.")
            self.txt_username.setFocus()
            return

        if not password:
            self.lbl_error.setText("⚠️ Por favor ingrese su contraseña.")
            self.txt_password.setFocus()
            return

        success = self.rbac_mgr.login(username, password)
        if success:
            self.authenticated_user = self.rbac_mgr.current_user
            self.lbl_error.setText("")
            self.accept()
        else:
            self.lbl_error.setText("❌ Credenciales incorrectas o usuario inactivo.")
            self.txt_password.selectAll()
            self.txt_password.setFocus()
