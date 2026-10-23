"""
VIGI-WIN PRO - Ventana de Alertas Prioritarias Flotante (Topmost)
Superpuesta en la esquina inferior derecha de Windows sobre la barra de tareas.
No roba el foco del teclado (non-activating) y soporta apilamiento ordenado de alertas simultáneas.
"""
import sys
from datetime import datetime
from typing import Optional, Callable, Dict, Any, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QApplication, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QColor, QFont, QCursor

from vigiwin.core.audio import AudioManager

class SingleAlertCard(QFrame):
    """Tarjeta individual de alerta dentro de la pila de notificaciones."""
    def __init__(self, alert_id: int, title: str, message: str, camera: str, priority: str,
                 on_accept: Callable[[int], None], on_silence: Callable[[int], None],
                 on_open_panel: Optional[Callable[[], None]] = None, parent=None):
        super().__init__(parent)
        self.alert_id = alert_id
        self.priority = priority
        self.on_accept = on_accept
        self.on_silence = on_silence
        self.on_open_panel = on_open_panel

        self.init_ui(title, message, camera, priority)

    def init_ui(self, title: str, message: str, camera: str, priority: str):
        self.setObjectName("alertCard")
        self.setAttribute(Qt.WA_StyledBackground, True)
        # Colores de borde y resplandor según prioridad
        is_critical = (priority == "Alta" or "Puerta" in title)
        border_color = "#ef4444" if is_critical else "#10b981"
        badge_bg = "#450a0a" if is_critical else "#064e3b"
        badge_fg = "#f87171" if is_critical else "#34d399"

        self.setStyleSheet(f"""
            QFrame#alertCard {{
                background-color: #0f172a;
                border: 2px solid {border_color};
                border-radius: 10px;
                padding: 10px;
            }}
        """)

        # Efecto de sombra difuminada
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(18)
        shadow.setColor(QColor(239, 68, 68, 90) if is_critical else QColor(16, 185, 129, 60))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Fila superior: Badge de Prioridad + Título + Origen
        top_row = QHBoxLayout()
        indicator = QLabel("●")
        indicator.setStyleSheet(f"color: {border_color}; font-size: 14px;")
        top_row.addWidget(indicator)

        lbl_title = QLabel(title.upper())
        lbl_title.setStyleSheet(f"color: {badge_fg}; font-weight: bold; font-size: 11px;")
        top_row.addWidget(lbl_title)

        top_row.addStretch()

        badge_prio = QLabel(f"PRIORIDAD {priority.upper()}")
        badge_prio.setStyleSheet(f"background-color: {badge_bg}; color: {badge_fg}; font-size: 9px; font-weight: bold; border-radius: 4px; padding: 2px 6px;")
        top_row.addWidget(badge_prio)

        layout.addLayout(top_row)

        # Mensaje
        lbl_msg = QLabel(message)
        lbl_msg.setWordWrap(True)
        lbl_msg.setStyleSheet("color: #f1f5f9; font-size: 11px; line-height: 1.3;")
        layout.addWidget(lbl_msg)

        # Pie: Fecha/Hora + Cámara + Botones de Acción
        bot_row = QHBoxLayout()
        time_str = datetime.now().strftime("%H:%M:%S")
        lbl_meta = QLabel(f"{camera} | {time_str}")
        lbl_meta.setStyleSheet("color: #64748b; font-size: 10px; font-family: monospace;")
        bot_row.addWidget(lbl_meta)

        bot_row.addStretch()

        # Botón Abrir Panel
        if self.on_open_panel:
            btn_panel = QPushButton("Ver")
            btn_panel.setCursor(QCursor(Qt.PointingHandCursor))
            btn_panel.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #94a3b8;
                    border: 1px solid #334155;
                    border-radius: 4px;
                    padding: 3px 7px;
                    font-size: 10px;
                }
                QPushButton:hover {
                    color: #ffffff;
                    border-color: #64748b;
                }
            """)
            btn_panel.clicked.connect(self.on_open_panel)
            bot_row.addWidget(btn_panel)

        # Botón Silenciar
        btn_silence = QPushButton("Silenciar")
        btn_silence.setCursor(QCursor(Qt.PointingHandCursor))
        btn_silence.setStyleSheet("""
            QPushButton {
                background: #1e293b;
                color: #cbd5e1;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 3px 8px;
                font-size: 10px;
            }
            QPushButton:hover {
                background: #334155;
                color: #ffffff;
            }
        """)
        btn_silence.clicked.connect(lambda: self.on_silence(self.alert_id))
        bot_row.addWidget(btn_silence)

        # Botón Aceptar
        btn_accept = QPushButton("Aceptar")
        btn_accept.setCursor(QCursor(Qt.PointingHandCursor))
        btn_accept.setStyleSheet("""
            QPushButton {
                background: #10b981;
                color: #020617;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                padding: 3px 10px;
                font-size: 10px;
            }
            QPushButton:hover {
                background: #059669;
            }
        """)
        btn_accept.clicked.connect(lambda: self.on_accept(self.alert_id))
        bot_row.addWidget(btn_accept)

        layout.addLayout(bot_row)


class CentralizedAlertOverlay(QWidget):
    """
    Contenedor principal de alertas flotantes.
    Mantiene la posición fija abajo a la derecha de la pantalla y no roba el foco de otras aplicaciones.
    """
    def __init__(self, db_manager, audio_manager: AudioManager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.audio = audio_manager
        self.cards: Dict[int, SingleAlertCard] = {}
        self.on_open_surveillance_callback: Optional[Callable[[], None]] = None

        self.init_window_properties()
        self.init_ui()

    def init_window_properties(self):
        # Flags para mantenerse siempre encima sin robar foco de otras aplicaciones
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedWidth(350)

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(8)

    def show_alert(self, title: str, message: str, camera: str = "CAM_01", priority: str = "Alta",
                   db_event_id: Optional[int] = None, auto_dismiss_sec: int = 0):
        """Dispara una nueva alerta visual y sonora."""
        alert_id = db_event_id or int(datetime.now().timestamp() * 1000)

        # Si ya existe una alerta activa para el mismo ID, no duplicar
        if alert_id in self.cards:
            return

        # Reproducir sonido según prioridad (con refuerzo acústico de Windows)
        if priority == "Alta" or "Puerta" in title:
            self.audio.play_critical_alarm()
        else:
            self.audio.play_chime()

        # Crear tarjeta
        card = SingleAlertCard(
            alert_id=alert_id,
            title=title,
            message=message,
            camera=camera,
            priority=priority,
            on_accept=self.handle_accept,
            on_silence=self.handle_silence,
            on_open_panel=self.on_open_surveillance_callback,
            parent=self
        )

        self.cards[alert_id] = card
        # Insertar al principio para apilar de forma ordenada
        self.main_layout.insertWidget(0, card)

        self.show()
        card.show()
        self.adjustSize()
        self.reposition_to_bottom_right()
        self.raise_()

        # Doble verificación de posicionamiento tras el primer render de Qt
        QTimer.singleShot(20, self.reposition_to_bottom_right)

        # Auto-cierre opcional para notificaciones informativas de baja prioridad
        if auto_dismiss_sec > 0:
            QTimer.singleShot(auto_dismiss_sec * 1000, lambda: self.dismiss_alert(alert_id))

    def handle_accept(self, alert_id: int):
        # Registrar confirmación en base de datos
        self.db.confirm_event(alert_id, "Operador")
        self.db.log_audit("Operador", "Alerta Confirmada", f"ID Alerta: {alert_id}")
        self.dismiss_alert(alert_id)

    def handle_silence(self, alert_id: int):
        self.db.log_audit("Operador", "Alerta Silenciada", f"ID Alerta: {alert_id}")
        self.dismiss_alert(alert_id)

    def dismiss_alert(self, alert_id: int):
        card = self.cards.pop(alert_id, None)
        if card:
            card.deleteLater()
            QTimer.singleShot(50, self._on_card_removed)

    def _on_card_removed(self):
        if not self.cards:
            self.hide()
        else:
            self.adjustSize()
            self.reposition_to_bottom_right()

    def reposition_to_bottom_right(self):
        """Calcula la posición exacta respetando la barra de tareas de Windows."""
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry() # Deduce la barra de tareas automáticamente
        if self.layout():
            self.layout().activate()
        self.adjustSize()
        hint = self.sizeHint()
        w = max(self.width(), hint.width(), 350)
        h = max(self.height(), hint.height(), 100)
        x = geo.right() - w - 20
        y = geo.bottom() - h - 20
        self.setGeometry(x, y, w, h)
        self.raise_()

        # Asegurar Topmost a nivel Win32 sin robar foco
        if sys.platform == 'win32':
            try:
                import ctypes
                from ctypes import wintypes
                hwnd = int(self.winId())
                user32 = ctypes.windll.user32
                user32.SetWindowPos.argtypes = [
                    wintypes.HWND, wintypes.HWND,
                    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                    ctypes.c_uint
                ]
                user32.SetWindowPos.restype = wintypes.BOOL
                HWND_TOPMOST = wintypes.HWND(-1)
                # SWP_NOACTIVATE = 0x0010, SWP_SHOWWINDOW = 0x0040
                user32.SetWindowPos(hwnd, HWND_TOPMOST, x, y, w, h, 0x0010 | 0x0040)
            except Exception:
                pass

    def resizeEvent(self, event):
        super().resizeEvent(event)
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.right() - self.width() - 20
            y = geo.bottom() - self.height() - 20
            self.move(x, y)
