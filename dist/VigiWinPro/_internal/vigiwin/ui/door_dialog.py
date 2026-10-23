"""
VIGI-WIN PRO - Diálogo de Aviso de Cierre de Puerta
Muestra confirmación al detectar el cierre de la puerta con botón «Aceptar» y registro de auditoría.
"""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor

class DoorClosedDialog(QDialog):
    def __init__(self, camera_id: str, duration_sec: float, on_confirm_callback=None, parent=None):
        super().__init__(parent)
        self.camera_id = camera_id
        self.duration_sec = duration_sec
        self.on_confirm_callback = on_confirm_callback

        self.setWindowTitle("Aviso del Sistema - Puerta Cerrada")
        self.setFixedSize(380, 200)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setStyleSheet("""
            QDialog {
                background-color: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 12px;
                color: #f8fafc;
            }
        """)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Encabezado con icono
        header = QHBoxLayout()
        icon = QLabel("🚪")
        icon.setStyleSheet("font-size: 24px;")
        header.addWidget(icon)

        title = QLabel("PUERTA CERRADA")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #10b981;")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        # Mensaje explicativo
        msg = QLabel(
            f"La puerta en <b>{self.camera_id}</b> ha sido cerrada correctamente.<br>"
            f"Tiempo total de apertura registrado: <b>{self.duration_sec} segundos</b>."
        )
        msg.setWordWrap(True)
        msg.setStyleSheet("font-size: 12px; color: #cbd5e1; line-height: 1.4;")
        layout.addWidget(msg)

        layout.addStretch()

        # Botón Aceptar
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_accept = QPushButton("Aceptar")
        btn_accept.setCursor(QCursor(Qt.PointingHandCursor))
        btn_accept.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: #020617;
                font-weight: bold;
                border-radius: 6px;
                padding: 8px 24px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #059669;
            }
        """)
        btn_accept.clicked.connect(self._handle_accept)
        btn_layout.addWidget(btn_accept)

        layout.addLayout(btn_layout)

    def _handle_accept(self):
        if self.on_confirm_callback:
            self.on_confirm_callback(self.camera_id, self.duration_sec)
        self.accept()
