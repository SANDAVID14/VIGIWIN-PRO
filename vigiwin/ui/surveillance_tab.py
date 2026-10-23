"""
VIGI-WIN PRO - Pestaña 1: Vigilancia en Directo
Visualizador de vídeo en tiempo real, selector de cámaras (USB, RTSP TCP, Simulador),
modo multi-cámara cuadrícula (Grid 2x2 / 1x1), calibración frontal/lateral,
temporizador de puerta, captura forense de evidencias y controles de simulación.
"""
import cv2
import numpy as np
from typing import Optional, Dict

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QComboBox, QSlider, QCheckBox, QSpinBox, QSizePolicy,
    QStackedWidget, QGridLayout, QScrollArea
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap, QCursor

from vigiwin.vision.door_detector import DoorDetector


class CameraGridTile(QFrame):
    """Tarjeta interactiva de vídeo para el modo cuadrícula 2x2."""
    clicked = Signal(str)
    double_clicked = Signal(str)

    def __init__(self, camera_id: str, camera_name: str, parent=None):
        super().__init__(parent)
        self.camera_id = camera_id
        self.camera_name = camera_name
        self.is_selected = False

        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.init_ui()
        self.set_selected(False)

    def init_ui(self):
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(6, 6, 6, 6)
        vbox.setSpacing(4)

        # Barra superior de la tarjeta: Título + Badge de estado
        hdr = QHBoxLayout()
        self.lbl_title = QLabel(f"📹 {self.camera_name}")
        self.lbl_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #f1f5f9;")
        hdr.addWidget(self.lbl_title)
        hdr.addStretch()

        self.lbl_badge = QLabel("EN LÍNEA")
        self.lbl_badge.setStyleSheet("font-size: 9px; font-family: monospace; background: #064e3b; color: #34d399; padding: 1px 5px; border-radius: 3px;")
        hdr.addWidget(self.lbl_badge)
        vbox.addLayout(hdr)

        # Superficie de vídeo
        self.video_label = QLabel("Conectando flujo...")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(180, 110)
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_label.setStyleSheet("background-color: #020617; border-radius: 4px; border: 1px solid #1e293b; color: #64748b; font-size: 10px;")
        vbox.addWidget(self.video_label)

        # Pie de la tarjeta: ID/FPS + Estado de Puerta
        ftr = QHBoxLayout()
        self.lbl_footer = QLabel(f"ID: {self.camera_id} | 30 FPS")
        self.lbl_footer.setStyleSheet("font-size: 10px; color: #64748b; font-family: monospace;")
        ftr.addWidget(self.lbl_footer)
        ftr.addStretch()
        self.lbl_state = QLabel("PUERTA: CERRADA")
        self.lbl_state.setStyleSheet("font-size: 10px; color: #10b981; font-weight: bold;")
        ftr.addWidget(self.lbl_state)
        vbox.addLayout(ftr)

    def set_selected(self, selected: bool):
        self.is_selected = selected
        if selected:
            self.setStyleSheet("""
                CameraGridTile {
                    background-color: #0b1120;
                    border: 2px solid #10b981;
                    border-radius: 8px;
                }
            """)
        else:
            self.setStyleSheet("""
                CameraGridTile {
                    background-color: #0f172a;
                    border: 1px solid #1e293b;
                    border-radius: 8px;
                }
                CameraGridTile:hover {
                    border: 1px solid #334155;
                }
            """)

    def mousePressEvent(self, event):
        self.clicked.emit(self.camera_id)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        self.double_clicked.emit(self.camera_id)
        super().mouseDoubleClickEvent(event)


class SurveillanceTab(QWidget):
    # Señales para comunicación desacoplada
    alert_requested = Signal(str, str, str, str) # title, message, camera, priority

    def __init__(self, camera_manager, db_manager, audio_manager, parent=None):
        super().__init__(parent)
        self.camera_manager = camera_manager
        self.db = db_manager
        self.audio = audio_manager

        self.current_perspective = "frontal"
        self.roi_visible = True
        self.view_mode = "1x1" # "1x1" o "2x2"
        self.grid_tiles: Dict[str, CameraGridTile] = {}

        self.init_ui()

        # Timer para actualización de fotogramas a ~30 FPS
        self.render_timer = QTimer(self)
        self.render_timer.timeout.connect(self.update_video_frame)
        self.render_timer.start(33)

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(14)

        # ----------------------------------------------------
        # COLUMNA IZQUIERDA: Visor de Vídeo + Simulación (2/3)
        # ----------------------------------------------------
        video_col = QVBoxLayout()
        video_col.setSpacing(10)

        # Panel contenedor de vídeo
        video_panel = QFrame()
        video_panel.setProperty("class", "glass-panel")
        video_panel.setStyleSheet("""
            QFrame.glass-panel {
                background-color: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 12px;
                padding: 10px;
            }
        """)
        video_panel_layout = QVBoxLayout(video_panel)
        video_panel_layout.setContentsMargins(10, 10, 10, 10)
        video_panel_layout.setSpacing(8)

        # Barra superior del visor: Selector de Modo Vista + Selector de Cámara + Botones
        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)

        # Selector de Vista: 1x1 Individual vs 2x2 Cuadrícula
        lbl_mode = QLabel("Vista:")
        lbl_mode.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: bold;")
        top_bar.addWidget(lbl_mode)

        self.btn_view_1x1 = QPushButton("⏹ 1x1")
        self.btn_view_1x1.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_view_1x1.setProperty("class", "btn-primary")
        self.btn_view_1x1.clicked.connect(lambda: self._set_view_mode("1x1"))
        top_bar.addWidget(self.btn_view_1x1)

        self.btn_view_2x2 = QPushButton("⊞ 2x2")
        self.btn_view_2x2.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_view_2x2.setProperty("class", "btn-secondary")
        self.btn_view_2x2.clicked.connect(lambda: self._set_view_mode("2x2"))
        top_bar.addWidget(self.btn_view_2x2)

        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color: #334155;")
        top_bar.addWidget(sep)

        # Selector de Cámara
        lbl_cam_icon = QLabel("📹")
        top_bar.addWidget(lbl_cam_icon)
        self.cam_combo = QComboBox()
        self.cam_combo.setMinimumWidth(200)
        self._refresh_camera_list()
        self.cam_combo.currentIndexChanged.connect(self._on_camera_changed)
        top_bar.addWidget(self.cam_combo)

        top_bar.addStretch()

        # Botón Vista Frontal
        self.btn_frontal = QPushButton("Vista Frontal")
        self.btn_frontal.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_frontal.setProperty("class", "btn-primary")
        self.btn_frontal.clicked.connect(lambda: self._set_perspective("frontal"))
        top_bar.addWidget(self.btn_frontal)

        # Botón Vista Lateral
        self.btn_lateral = QPushButton("Vista Lateral")
        self.btn_lateral.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_lateral.setProperty("class", "btn-secondary")
        self.btn_lateral.clicked.connect(lambda: self._set_perspective("lateral"))
        top_bar.addWidget(self.btn_lateral)

        # Botón Alternar ROI
        self.btn_roi = QPushButton("Marco ROI: ON")
        self.btn_roi.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_roi.setProperty("class", "btn-secondary")
        self.btn_roi.clicked.connect(self._toggle_roi)
        top_bar.addWidget(self.btn_roi)

        # Botón Calibrar
        self.btn_calibrate = QPushButton("Calibrar Cerrado")
        self.btn_calibrate.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_calibrate.setStyleSheet("""
            QPushButton {
                background-color: #064e3b;
                color: #34d399;
                border: 1px solid #059669;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #047857;
            }
        """)
        self.btn_calibrate.clicked.connect(self._calibrate_reference)
        top_bar.addWidget(self.btn_calibrate)

        video_panel_layout.addLayout(top_bar)

        # ----------------------------------------------------
        # STACK DE VÍDEO: Página 0 (1x1) y Página 1 (Cuadrícula 2x2)
        # ----------------------------------------------------
        self.video_stack = QStackedWidget()

        # Página 0: Vista 1x1 Individual
        single_page = QWidget()
        single_layout = QVBoxLayout(single_page)
        single_layout.setContentsMargins(0, 0, 0, 0)
        self.video_label = QLabel("Cargando flujo de vídeo...")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(420, 236)
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_label.setStyleSheet("background-color: #020617; border-radius: 8px; border: 1px solid #1e293b;")
        single_layout.addWidget(self.video_label)
        self.video_stack.addWidget(single_page)

        # Página 1: Cuadrícula 2x2 Multi-Cámara
        self.grid_page = QWidget()
        self.grid_layout = QGridLayout(self.grid_page)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(8)
        self._build_grid_tiles()
        self.video_stack.addWidget(self.grid_page)

        video_panel_layout.addWidget(self.video_stack)

        # Barra de Estado del Vídeo (FPS + Temporizador de Puerta)
        status_bar = QHBoxLayout()
        self.lbl_fps = QLabel("FPS: 30.0 | IA: OpenCV + PySide6")
        self.lbl_fps.setStyleSheet("color: #10b981; font-family: monospace; font-size: 11px;")
        status_bar.addWidget(self.lbl_fps)

        status_bar.addStretch()

        self.lbl_door_timer_badge = QLabel("Puerta: CERRADA | 00:00")
        self.lbl_door_timer_badge.setStyleSheet("""
            background-color: #0b1120;
            color: #10b981;
            border: 1px solid #1e293b;
            border-radius: 6px;
            padding: 4px 12px;
            font-family: monospace;
            font-size: 11px;
            font-weight: bold;
        """)
        status_bar.addWidget(self.lbl_door_timer_badge)

        video_panel_layout.addLayout(status_bar)
        video_col.addWidget(video_panel)

        # Panel de Controles de Simulación del Sensor
        sim_panel = QFrame()
        sim_panel.setProperty("class", "glass-panel")
        sim_panel.setStyleSheet("""
            QFrame.glass-panel {
                background-color: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 12px;
                padding: 10px;
            }
        """)
        sim_layout = QHBoxLayout(sim_panel)
        sim_layout.setContentsMargins(12, 10, 12, 10)
        sim_layout.setSpacing(10)

        lbl_sim_title = QLabel("Simulación de Sensor:")
        lbl_sim_title.setStyleSheet("font-weight: bold; color: #cbd5e1; font-size: 11px;")
        sim_layout.addWidget(lbl_sim_title)

        # Botón Simular Puerta Abierta (>60 seg)
        self.btn_sim_open = QPushButton("Simular Puerta Abierta (≥60 seg)")
        self.btn_sim_open.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_sim_open.setProperty("class", "btn-amber")
        self.btn_sim_open.clicked.connect(self._simulate_open_door)
        sim_layout.addWidget(self.btn_sim_open)

        # Botón Probar Alarma Inmediata
        self.btn_sim_alarm_now = QPushButton("⚡ Probar Alarma Inmediata (>60s)")
        self.btn_sim_alarm_now.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_sim_alarm_now.setStyleSheet("""
            QPushButton {
                background-color: rgba(220, 38, 38, 0.25);
                color: #fca5a5;
                border: 1px solid rgba(239, 68, 68, 0.6);
                border-radius: 6px;
                padding: 7px 12px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(220, 38, 38, 0.4);
            }
        """)
        self.btn_sim_alarm_now.clicked.connect(self._simulate_immediate_alarm)
        sim_layout.addWidget(self.btn_sim_alarm_now)

        # Botón Cerrar Puerta
        self.btn_sim_close = QPushButton("Cerrar Puerta")
        self.btn_sim_close.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_sim_close.setProperty("class", "btn-secondary")
        self.btn_sim_close.clicked.connect(self._simulate_close_door)
        sim_layout.addWidget(self.btn_sim_close)

        sim_layout.addStretch()

        # Botón Forzar Evento Detección
        self.btn_force_event = QPushButton("+ Forzar Detección")
        self.btn_force_event.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_force_event.setProperty("class", "btn-secondary")
        self.btn_force_event.clicked.connect(self._simulate_random_detection)
        sim_layout.addWidget(self.btn_force_event)

        video_col.addWidget(sim_panel)
        main_layout.addLayout(video_col, stretch=7)

        # ----------------------------------------------------
        # COLUMNA DERECHA: Controles de Inteligencia Artificial (1/3)
        # ----------------------------------------------------
        ai_panel = QFrame()
        ai_panel.setProperty("class", "glass-panel")
        ai_panel.setMaximumWidth(340)
        ai_panel.setStyleSheet("""
            QFrame.glass-panel {
                background-color: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 12px;
                padding: 14px;
            }
        """)
        ai_layout = QVBoxLayout(ai_panel)
        ai_layout.setContentsMargins(12, 12, 12, 12)
        ai_layout.setSpacing(14)

        lbl_ai_header = QLabel("MOTORES DE INTELIGENCIA ARTIFICIAL")
        lbl_ai_header.setStyleSheet("color: #94a3b8; font-weight: bold; font-size: 11px; letter-spacing: 0.5px;")
        ai_layout.addWidget(lbl_ai_header)

        # 1. Módulo Detectar Personas (Interruptor Independiente)
        person_box = QFrame()
        person_box.setStyleSheet("background-color: #090e1a; border: 1px solid #1e293b; border-radius: 8px; padding: 10px;")
        person_layout = QVBoxLayout(person_box)
        person_layout.setSpacing(8)

        person_header = QHBoxLayout()
        self.chk_person = QCheckBox("Detectar Personas")
        self.chk_person.setChecked(True)
        self.chk_person.stateChanged.connect(self._on_person_toggle)
        person_header.addWidget(self.chk_person)
        person_header.addStretch()
        self.lbl_person_status = QLabel("ACTIVO")
        self.lbl_person_status.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 10px; font-family: monospace;")
        person_header.addWidget(self.lbl_person_status)
        person_layout.addLayout(person_header)

        # Sensibilidad Personas
        sens_p_row = QHBoxLayout()
        lbl_sens_p = QLabel("Sensibilidad:")
        lbl_sens_p.setStyleSheet("color: #94a3b8; font-size: 11px;")
        sens_p_row.addWidget(lbl_sens_p)
        self.lbl_p_sens_val = QLabel("80%")
        self.lbl_p_sens_val.setStyleSheet("color: #10b981; font-weight: bold; font-size: 11px;")
        sens_p_row.addWidget(self.lbl_p_sens_val)
        person_layout.addLayout(sens_p_row)

        self.slider_person_sens = QSlider(Qt.Horizontal)
        self.slider_person_sens.setRange(10, 100)
        self.slider_person_sens.setValue(80)
        self.slider_person_sens.valueChanged.connect(self._on_person_sens_changed)
        person_layout.addWidget(self.slider_person_sens)
        ai_layout.addWidget(person_box)

        # 2. Módulo Detectar Vehículos (Interruptor Independiente)
        vehicle_box = QFrame()
        vehicle_box.setStyleSheet("background-color: #090e1a; border: 1px solid #1e293b; border-radius: 8px; padding: 10px;")
        vehicle_layout = QVBoxLayout(vehicle_box)
        vehicle_layout.setSpacing(8)

        vehicle_header = QHBoxLayout()
        self.chk_vehicle = QCheckBox("Detectar Vehículos")
        self.chk_vehicle.setChecked(True)
        self.chk_vehicle.stateChanged.connect(self._on_vehicle_toggle)
        vehicle_header.addWidget(self.chk_vehicle)
        vehicle_header.addStretch()
        self.lbl_vehicle_status = QLabel("ACTIVO")
        self.lbl_vehicle_status.setStyleSheet("color: #f59e0b; font-weight: bold; font-size: 10px; font-family: monospace;")
        vehicle_header.addWidget(self.lbl_vehicle_status)
        vehicle_layout.addLayout(vehicle_header)

        # Sensibilidad Vehículos
        sens_v_row = QHBoxLayout()
        lbl_sens_v = QLabel("Sensibilidad:")
        lbl_sens_v.setStyleSheet("color: #94a3b8; font-size: 11px;")
        sens_v_row.addWidget(lbl_sens_v)
        self.lbl_v_sens_val = QLabel("75%")
        self.lbl_v_sens_val.setStyleSheet("color: #10b981; font-weight: bold; font-size: 11px;")
        sens_v_row.addWidget(self.lbl_v_sens_val)
        vehicle_layout.addLayout(sens_v_row)

        self.slider_vehicle_sens = QSlider(Qt.Horizontal)
        self.slider_vehicle_sens.setRange(10, 100)
        self.slider_vehicle_sens.setValue(75)
        self.slider_vehicle_sens.valueChanged.connect(self._on_vehicle_sens_changed)
        vehicle_layout.addWidget(self.slider_vehicle_sens)
        ai_layout.addWidget(vehicle_box)

        # 3. Reglas de Vigilancia de Puerta y Temporizador
        door_rules_box = QFrame()
        door_rules_box.setStyleSheet("background-color: #090e1a; border: 1px solid #1e293b; border-radius: 8px; padding: 10px;")
        door_rules_layout = QVBoxLayout(door_rules_box)
        door_rules_layout.setSpacing(8)

        lbl_dr_header = QLabel("REGLAS DE VIGILANCIA DE PUERTA")
        lbl_dr_header.setStyleSheet("color: #cbd5e1; font-weight: bold; font-size: 10px;")
        door_rules_layout.addWidget(lbl_dr_header)

        # Temporizador ajustable en segundos / minutos
        timer_row = QHBoxLayout()
        lbl_t_text = QLabel("Tiempo Máx. Abierta:")
        lbl_t_text.setStyleSheet("color: #94a3b8; font-size: 11px;")
        timer_row.addWidget(lbl_t_text)

        self.spin_door_time = QSpinBox()
        self.spin_door_time.setRange(5, 3600)
        self.spin_door_time.setValue(60)
        self.spin_door_time.setSuffix(" seg")
        self.spin_door_time.setSingleStep(5)
        self.spin_door_time.valueChanged.connect(self._on_door_time_changed)
        timer_row.addWidget(self.spin_door_time)
        door_rules_layout.addLayout(timer_row)

        # Umbral Variación de Posición (10% fijo según especificación)
        var_row = QHBoxLayout()
        lbl_var = QLabel("Umbral de Variación:")
        lbl_var.setStyleSheet("color: #94a3b8; font-size: 11px;")
        var_row.addWidget(lbl_var)
        lbl_var_val = QLabel("10% (Fijo)")
        lbl_var_val.setStyleSheet("color: #10b981; font-weight: bold; font-size: 11px;")
        var_row.addWidget(lbl_var_val)
        door_rules_layout.addLayout(var_row)

        # Prioridad Alerta
        prio_row = QHBoxLayout()
        lbl_prio = QLabel("Prioridad de Alarma:")
        lbl_prio.setStyleSheet("color: #94a3b8; font-size: 11px;")
        prio_row.addWidget(lbl_prio)
        lbl_prio_val = QLabel("ALTA / CRÍTICA")
        lbl_prio_val.setStyleSheet("background-color: #450a0a; color: #f87171; border: 1px solid #7f1d1d; border-radius: 4px; padding: 2px 6px; font-weight: bold; font-size: 10px;")
        prio_row.addWidget(lbl_prio_val)
        door_rules_layout.addLayout(prio_row)

        ai_layout.addWidget(door_rules_box)
        ai_layout.addStretch()

        scroll_ai = QScrollArea()
        scroll_ai.setWidgetResizable(True)
        scroll_ai.setMaximumWidth(360)
        scroll_ai.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: #0f172a;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #334155;
                border-radius: 4px;
            }
        """)
        scroll_ai.setWidget(ai_panel)

        main_layout.addWidget(scroll_ai, stretch=3)

    # -----------------------------------------------------------------
    # Gestión del Modo Cuadrícula 2x2
    # -----------------------------------------------------------------
    def _build_grid_tiles(self):
        """Construye las 4 tarjetas del modo cuadrícula 2x2."""
        # Limpiar
        for tile in self.grid_tiles.values():
            self.grid_layout.removeWidget(tile)
            tile.deleteLater()
        self.grid_tiles.clear()

        # Obtener primeras 4 cámaras o canales
        cams = list(self.camera_manager.streams.keys())[:4]
        if not cams:
            cams = ["CAM_01"]

        # Si hay menos de 4 cámaras, rellenar hasta 4 con nombres descriptivos
        positions = [(0, 0), (0, 1), (1, 0), (1, 1)]
        for idx, (r, c) in enumerate(positions):
            if idx < len(cams):
                cid = cams[idx]
                stream = self.camera_manager.streams[cid]
                tile = CameraGridTile(cid, stream.name, parent=self)
                tile.clicked.connect(self._on_grid_tile_clicked)
                tile.double_clicked.connect(self._on_grid_tile_double_clicked)
                self.grid_layout.addWidget(tile, r, c)
                self.grid_tiles[cid] = tile
            else:
                # Ranura vacía/disponible
                slot_id = f"CH_{idx+1:02d}"
                tile = CameraGridTile(slot_id, f"Canal #{idx+1} (Libre)", parent=self)
                tile.lbl_badge.setText("DISPONIBLE")
                tile.lbl_badge.setStyleSheet("font-size: 9px; font-family: monospace; background: #1e293b; color: #94a3b8; padding: 1px 5px; border-radius: 3px;")
                tile.lbl_state.setText("INACTIVO")
                tile.lbl_state.setStyleSheet("font-size: 10px; color: #64748b;")
                self.grid_layout.addWidget(tile, r, c)

    def _set_view_mode(self, mode: str):
        self.view_mode = mode
        if mode == "1x1":
            self.video_stack.setCurrentIndex(0)
            self.btn_view_1x1.setProperty("class", "btn-primary")
            self.btn_view_2x2.setProperty("class", "btn-secondary")
        else:
            self.camera_manager.start_all()
            self._build_grid_tiles()
            self.video_stack.setCurrentIndex(1)
            self.btn_view_1x1.setProperty("class", "btn-secondary")
            self.btn_view_2x2.setProperty("class", "btn-primary")

        # Forzar refresco de estilos en los botones
        for btn in (self.btn_view_1x1, self.btn_view_2x2):
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _on_grid_tile_clicked(self, camera_id: str):
        if camera_id in self.camera_manager.streams:
            self._select_camera_by_id(camera_id)
            for cid, tile in self.grid_tiles.items():
                tile.set_selected(cid == camera_id)

    def _on_grid_tile_double_clicked(self, camera_id: str):
        if camera_id in self.camera_manager.streams:
            self._select_camera_by_id(camera_id)
            self._set_view_mode("1x1")

    def _select_camera_by_id(self, camera_id: str):
        idx = self.cam_combo.findData(camera_id)
        if idx >= 0:
            self.cam_combo.setCurrentIndex(idx)
        else:
            self.camera_manager.set_active_camera(camera_id)

    def _refresh_camera_list(self):
        self.cam_combo.clear()
        cams = self.db.get_cameras()
        for c in cams:
            self.cam_combo.addItem(f"{c['id']} - {c['name']} ({c['source_type'].upper()})", c["id"])

    def _on_camera_changed(self, index: int):
        cam_id = self.cam_combo.currentData()
        if cam_id:
            self.camera_manager.set_active_camera(cam_id)
            cam = self.db.get_camera(cam_id)
            if cam:
                self.spin_door_time.setValue(cam.get("door_max_open_sec", 60))
                self.chk_person.setChecked(bool(cam.get("detect_person", 1)))
                self.chk_vehicle.setChecked(bool(cam.get("detect_vehicle", 1)))
                self.slider_person_sens.setValue(cam.get("person_sensitivity", 80))
                self.slider_vehicle_sens.setValue(cam.get("vehicle_sensitivity", 75))
                self._set_perspective(cam.get("perspective", "frontal"), update_db=False)
            # Actualizar resaltado en cuadrícula si está visible
            for cid, tile in self.grid_tiles.items():
                tile.set_selected(cid == cam_id)

    def _set_perspective(self, perspective: str, update_db: bool = True):
        self.current_perspective = perspective
        cid = self.camera_manager.active_camera_id
        door_det = self.camera_manager.door_detectors.get(cid)
        if door_det:
            door_det.set_perspective(perspective)
        stream = self.camera_manager.streams.get(cid)
        if stream:
            stream.sim_perspective = perspective

        if perspective == "frontal":
            self.btn_frontal.setProperty("class", "btn-primary")
            self.btn_lateral.setProperty("class", "btn-secondary")
        else:
            self.btn_frontal.setProperty("class", "btn-secondary")
            self.btn_lateral.setProperty("class", "btn-primary")

        self.btn_frontal.style().unpolish(self.btn_frontal)
        self.btn_frontal.style().polish(self.btn_frontal)
        self.btn_lateral.style().unpolish(self.btn_lateral)
        self.btn_lateral.style().polish(self.btn_lateral)

        if update_db and door_det:
            self.db.update_camera_calibration(cid, perspective, door_det.roi)

    def _toggle_roi(self):
        self.roi_visible = not self.roi_visible
        self.camera_manager.show_roi = self.roi_visible
        self.btn_roi.setText(f"Marco ROI: {'ON' if self.roi_visible else 'OFF'}")

    def _calibrate_reference(self):
        cid = self.camera_manager.active_camera_id
        stream = self.camera_manager.streams.get(cid)
        door_det = self.camera_manager.door_detectors.get(cid)
        if stream and door_det:
            ret, frame, _ = stream.read_frame()
            if ret and frame is not None:
                door_det.calibrate_closed_reference(frame)
                self.db.update_camera_calibration(cid, self.current_perspective, door_det.roi)
                self.db.log_audit("Operador", "Calibración de Puerta", f"Cámara: {cid}")
                self.audio.play_chime()

    def _on_person_toggle(self, state: int):
        enabled = (state == Qt.Checked.value or state == 2)
        cid = self.camera_manager.active_camera_id
        obj_det = self.camera_manager.object_detectors.get(cid)
        if obj_det:
            obj_det.set_person_enabled(enabled)
            self.lbl_person_status.setText("ACTIVO" if enabled else "DESACTIVADO")
            self.lbl_person_status.setStyleSheet("color: #38bdf8;" if enabled else "color: #64748b;")
        # Actualizar persistencia
        cam = self.db.get_camera(cid)
        if cam:
            cam["detect_person"] = 1 if enabled else 0
            self.db.save_camera(cam)

    def _on_vehicle_toggle(self, state: int):
        enabled = (state == Qt.Checked.value or state == 2)
        cid = self.camera_manager.active_camera_id
        obj_det = self.camera_manager.object_detectors.get(cid)
        if obj_det:
            obj_det.set_vehicle_enabled(enabled)
            self.lbl_vehicle_status.setText("ACTIVO" if enabled else "DESACTIVADO")
            self.lbl_vehicle_status.setStyleSheet("color: #f59e0b;" if enabled else "color: #64748b;")
        # Actualizar persistencia
        cam = self.db.get_camera(cid)
        if cam:
            cam["detect_vehicle"] = 1 if enabled else 0
            self.db.save_camera(cam)

    def _on_person_sens_changed(self, value: int):
        self.lbl_p_sens_val.setText(f"{value}%")
        cid = self.camera_manager.active_camera_id
        obj_det = self.camera_manager.object_detectors.get(cid)
        if obj_det:
            obj_det.set_sensitivities(value, self.slider_vehicle_sens.value())

    def _on_vehicle_sens_changed(self, value: int):
        self.lbl_v_sens_val.setText(f"{value}%")
        cid = self.camera_manager.active_camera_id
        obj_det = self.camera_manager.object_detectors.get(cid)
        if obj_det:
            obj_det.set_sensitivities(self.slider_person_sens.value(), value)

    def _on_door_time_changed(self, value: int):
        cid = self.camera_manager.active_camera_id
        door_det = self.camera_manager.door_detectors.get(cid)
        if door_det:
            door_det.max_open_seconds = value
        cam = self.db.get_camera(cid)
        if cam:
            cam["door_max_open_sec"] = value
            self.db.save_camera(cam)

    def _simulate_open_door(self):
        cid = self.camera_manager.active_camera_id
        stream = self.camera_manager.streams.get(cid)
        if stream:
            stream.set_simulation_door_open(True)
        # Log en base de datos con snapshot forense
        snap_path = self.camera_manager.save_snapshot(cid, "Apertura_Puerta")
        self.db.log_event(cid, "Apertura Puerta", "Apertura de puerta detectada por sensor de posición", "Media", snapshot_path=snap_path)

    def _simulate_immediate_alarm(self):
        cid = self.camera_manager.active_camera_id
        stream = self.camera_manager.streams.get(cid)
        door_det = self.camera_manager.door_detectors.get(cid)
        if stream:
            stream.set_simulation_door_open(True)
        if door_det:
            import time
            door_det.door_open_start_time = time.monotonic() - door_det.max_open_seconds - 5
            door_det.elapsed_open_seconds = door_det.max_open_seconds + 5
            door_det.current_state = DoorDetector.STATE_ALARM
            door_det.alarm_triggered = True
            door_det.alarm_triggered_reported = False
        msg = f"¡Atención! La puerta en {cid} permanece abierta por más de 60 segundos consecutivos."
        snap_path = self.camera_manager.save_snapshot(cid, "Alerta_Puerta")
        eid = self.db.log_event(cid, "Alerta Puerta", msg, "Alta", snapshot_path=snap_path)
        door_res = {
            "camera_id": cid,
            "elapsed_seconds": 65.0,
            "variation_pct": 85.0,
            "state": DoorDetector.STATE_ALARM,
            "is_alarm": True
        }
        if self.camera_manager.on_door_alarm_callback:
            self.camera_manager.on_door_alarm_callback(door_res)
        else:
            self.alert_requested.emit("ALERTA CRÍTICA: PUERTA ABIERTA", msg, cid, "Alta")

    def _simulate_close_door(self):
        cid = self.camera_manager.active_camera_id
        stream = self.camera_manager.streams.get(cid)
        if stream:
            stream.set_simulation_door_open(False)

    def _simulate_random_detection(self):
        import random
        cid = self.camera_manager.active_camera_id
        types = [
            ("Persona", "Persona detectada en zona perimetral", "Media"),
            ("Vehículo", "Vehículo (Automóvil) detectado en acceso", "Media"),
            ("Puerta", "Variación detectada en talanquera", "Media")
        ]
        t, msg, prio = random.choice(types)
        snap_path = self.camera_manager.save_snapshot(cid, t)
        eid = self.db.log_event(cid, t, msg, prio, snapshot_path=snap_path)
        self.alert_requested.emit(f"Detección {t}", msg, cid, prio)

    def update_video_frame(self):
        """Actualiza el fotograma en pantalla y el temporizador en tiempo real."""
        if self.view_mode == "1x1":
            res = self.camera_manager.process_active_frame()
            frame = res.get("frame")
            if frame is not None:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb.shape
                bytes_per_line = ch * w
                q_img = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
                pix = QPixmap.fromImage(q_img).scaled(
                    self.video_label.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.video_label.setPixmap(pix)

            fps = res.get("fps", 0.0)
            self.lbl_fps.setText(f"FPS: {fps:.1f} | IA: OpenCV + PySide6")
            self._update_door_badge(res.get("door_result", {}))
        else:
            # Modo Cuadrícula 2x2: procesar y actualizar los 4 canales simultáneos
            active_cid = self.camera_manager.active_camera_id
            for cid, tile in self.grid_tiles.items():
                if cid not in self.camera_manager.streams:
                    continue
                res = self.camera_manager.process_camera_frame(cid)
                frame = res.get("frame")
                if frame is not None:
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    h, w, ch = rgb.shape
                    bytes_per_line = ch * w
                    q_img = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
                    pix = QPixmap.fromImage(q_img).scaled(
                        tile.video_label.size(),
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    )
                    tile.video_label.setPixmap(pix)

                door_res = res.get("door_result", {})
                state = door_res.get("state", "CERRADO")
                if state == DoorDetector.STATE_ALARM:
                    tile.lbl_state.setText(f"ALARMA ({door_res.get('elapsed_seconds', 0):.0f}s)")
                    tile.lbl_state.setStyleSheet("font-size: 10px; color: #ef4444; font-weight: bold;")
                    tile.lbl_badge.setText("ALERTA")
                    tile.lbl_badge.setStyleSheet("font-size: 9px; font-family: monospace; background: #7f1d1d; color: #fca5a5; padding: 1px 5px; border-radius: 3px;")
                elif state == DoorDetector.STATE_OPEN:
                    tile.lbl_state.setText(f"ABIERTA ({door_res.get('elapsed_seconds', 0):.0f}s)")
                    tile.lbl_state.setStyleSheet("font-size: 10px; color: #f59e0b; font-weight: bold;")
                    tile.lbl_badge.setText("ABIERTA")
                    tile.lbl_badge.setStyleSheet("font-size: 9px; font-family: monospace; background: #78350f; color: #fcd34d; padding: 1px 5px; border-radius: 3px;")
                else:
                    tile.lbl_state.setText("CERRADA")
                    tile.lbl_state.setStyleSheet("font-size: 10px; color: #10b981; font-weight: bold;")
                    tile.lbl_badge.setText("EN LÍNEA")
                    tile.lbl_badge.setStyleSheet("font-size: 9px; font-family: monospace; background: #064e3b; color: #34d399; padding: 1px 5px; border-radius: 3px;")

                fps = res.get("fps", 30.0)
                tile.lbl_footer.setText(f"ID: {cid} | {fps:.0f} FPS")
                tile.set_selected(cid == active_cid)

                if cid == active_cid:
                    self._update_door_badge(door_res)

            self.lbl_fps.setText(f"Modo Cuadrícula 2x2 | 4 Canales Simultáneos | Activa: {active_cid}")

    def _update_door_badge(self, door_res: dict):
        state = door_res.get("state", "CERRADO")
        elapsed = door_res.get("elapsed_seconds", 0.0)
        mins = int(elapsed // 60)
        secs = int(elapsed % 60)
        time_str = f"{mins:02d}:{secs:02d}"

        if state == DoorDetector.STATE_ALARM:
            self.lbl_door_timer_badge.setText(f"ALERTA PUERTA: ABIERTA ({time_str})")
            self.lbl_door_timer_badge.setStyleSheet("""
                background-color: #450a0a;
                color: #ef4444;
                border: 1px solid #b91c1c;
                border-radius: 6px;
                padding: 4px 12px;
                font-family: monospace;
                font-size: 11px;
                font-weight: bold;
            """)
        elif state == DoorDetector.STATE_OPEN:
            self.lbl_door_timer_badge.setText(f"Puerta: ABIERTA | {time_str}")
            self.lbl_door_timer_badge.setStyleSheet("""
                background-color: #451a03;
                color: #f59e0b;
                border: 1px solid #b45309;
                border-radius: 6px;
                padding: 4px 12px;
                font-family: monospace;
                font-size: 11px;
                font-weight: bold;
            """)
        elif state == DoorDetector.STATE_UNCERTAIN:
            self.lbl_door_timer_badge.setText("Puerta: INCERTIDUMBRE")
            self.lbl_door_timer_badge.setStyleSheet("""
                background-color: #362e08;
                color: #facc15;
                border: 1px solid #ca8a04;
                border-radius: 6px;
                padding: 4px 12px;
                font-family: monospace;
                font-size: 11px;
                font-weight: bold;
            """)
        else:
            self.lbl_door_timer_badge.setText("Puerta: CERRADA | 00:00")
            self.lbl_door_timer_badge.setStyleSheet("""
                background-color: #0b1120;
                color: #10b981;
                border: 1px solid #1e293b;
                border-radius: 6px;
                padding: 4px 12px;
                font-family: monospace;
                font-size: 11px;
                font-weight: bold;
            """)

    def apply_role_permissions(self, role: str):
        """Aplica restricciones dinámicas de interfaz según el rol RBAC."""
        can_act = role in ["Administrador", "Operador de Seguridad"]
        self.btn_sim_open.setEnabled(can_act)
        self.btn_sim_alarm_now.setEnabled(can_act)
        self.btn_sim_close.setEnabled(can_act)

        if not can_act:
            self.btn_sim_open.setToolTip("Restringido: El rol Auditor no tiene permiso para disparar simulaciones.")
            self.btn_sim_alarm_now.setToolTip("Restringido: El rol Auditor no tiene permiso para disparar alarmas.")
            self.btn_sim_close.setToolTip("Restringido: El rol Auditor no tiene permiso para alterar el sensor.")
        else:
            self.btn_sim_open.setToolTip("")
            self.btn_sim_alarm_now.setToolTip("")
            self.btn_sim_close.setToolTip("")
