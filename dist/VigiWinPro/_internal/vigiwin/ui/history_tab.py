"""
VIGI-WIN PRO - Pestaña 2: Historial & Alertas Registradas
Consulta y filtrado en tiempo real sobre la base de datos SQLite (~/.vigiwinpro/vigiwin.db),
búsqueda por texto, filtro de categorías, acuse de recibo, visor forense de evidencias (snapshots) y exportación a CSV.
"""
import os
import subprocess
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog, QMessageBox, QFrame, QDialog,
    QSizePolicy, QSplitter
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QCursor, QPixmap, QImage

from vigiwin.core.config import get_snapshots_dir


class SnapshotViewerDialog(QDialog):
    """Diálogo modal de alta resolución para inspección forense de la captura."""
    def __init__(self, image_path: str, event_data: dict, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.event_data = event_data

        cam = event_data.get("camera", "Cámara")
        etype = event_data.get("event_type", "Alerta")
        ts = event_data.get("timestamp", "")
        self.setWindowTitle(f"Inspección Forense de Evidencia | {cam} - {etype} ({ts})")
        self.resize(920, 640)
        self.setStyleSheet("""
            QDialog {
                background-color: #0b1120;
                color: #f8fafc;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Barra superior informativa
        header = QHBoxLayout()
        meta_box = QVBoxLayout()
        lbl_title = QLabel(f"📷 Evidencia Fotográfica: {cam} — {etype}")
        lbl_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #34d399;")
        meta_box.addWidget(lbl_title)

        lbl_desc = QLabel(f"Fecha/Hora: {ts} | Mensaje: {event_data.get('message', '')}")
        lbl_desc.setStyleSheet("font-size: 11px; color: #94a3b8;")
        meta_box.addWidget(lbl_desc)
        header.addLayout(meta_box)
        header.addStretch()

        btn_save = QPushButton("💾 Guardar Como...")
        btn_save.setCursor(QCursor(Qt.PointingHandCursor))
        btn_save.setStyleSheet("""
            QPushButton {
                background-color: #064e3b;
                color: #34d399;
                border: 1px solid #059669;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #047857;
            }
        """)
        btn_save.clicked.connect(self._save_image_as)
        header.addWidget(btn_save)

        btn_close = QPushButton("Cerrar")
        btn_close.setCursor(QCursor(Qt.PointingHandCursor))
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #cbd5e1;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #334155;
            }
        """)
        btn_close.clicked.connect(self.accept)
        header.addWidget(btn_close)

        layout.addLayout(header)

        # Visualizador de imagen
        self.lbl_image = QLabel()
        self.lbl_image.setAlignment(Qt.AlignCenter)
        self.lbl_image.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.lbl_image.setStyleSheet("background-color: #020617; border: 1px solid #1e293b; border-radius: 8px;")
        layout.addWidget(self.lbl_image)

        self._load_image()

    def _load_image(self):
        if os.path.exists(self.image_path):
            pix = QPixmap(self.image_path)
            if not pix.isNull():
                self.lbl_image.setPixmap(pix.scaled(
                    880, 520,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                ))
            else:
                self.lbl_image.setText("No se pudo decodificar el archivo de imagen.")
        else:
            self.lbl_image.setText("Archivo de imagen no encontrado en disco.")

    def _save_image_as(self):
        if not os.path.exists(self.image_path):
            return
        dest, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Evidencia Fotográfica",
            os.path.basename(self.image_path),
            "Imágenes JPEG (*.jpg *.jpeg)"
        )
        if dest:
            import shutil
            try:
                shutil.copy2(self.image_path, dest)
                QMessageBox.information(self, "Guardado Exitoso", f"Copia de evidencia guardada en:\n{dest}")
            except Exception as e:
                QMessageBox.warning(self, "Error al Guardar", f"No se pudo guardar la imagen: {e}")


class HistoryTab(QWidget):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.current_events = []
        self.selected_event = None

        self.init_ui()
        self.refresh_table()

        # Actualizar automáticamente cada 4 segundos
        self.auto_refresh_timer = QTimer(self)
        self.auto_refresh_timer.timeout.connect(self.refresh_table)
        self.auto_refresh_timer.start(4000)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        # Panel Contenedor Principal
        container = QFrame()
        container.setProperty("class", "glass-panel")
        container.setStyleSheet("""
            QFrame.glass-panel {
                background-color: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 12px;
                padding: 14px;
            }
        """)
        panel_layout = QVBoxLayout(container)
        panel_layout.setSpacing(12)

        # Barra Superior: Títulos + Filtros + Botón Exportar
        top_bar = QHBoxLayout()

        # Título y ruta de la base de datos
        title_box = QVBoxLayout()
        lbl_title = QLabel("Historial de Eventos, Alarmas y Evidencias Fotográficas")
        lbl_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #f8fafc;")
        title_box.addWidget(lbl_title)

        lbl_subtitle = QLabel("Persistencia SQLite en tiempo real (~/.vigiwinpro/vigiwin.db)")
        lbl_subtitle.setStyleSheet("font-size: 11px; color: #64748b; font-family: monospace;")
        title_box.addWidget(lbl_subtitle)
        top_bar.addLayout(title_box)

        top_bar.addStretch()

        # Campo de Búsqueda
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Buscar evento...")
        self.txt_search.setMinimumWidth(180)
        self.txt_search.textChanged.connect(self.refresh_table)
        top_bar.addWidget(self.txt_search)

        # Selector de Categoría
        self.combo_category = QComboBox()
        self.combo_category.addItems(["Todas las Categorías", "Puerta", "Persona", "Vehículo", "Fallo", "Sistema"])
        self.combo_category.currentIndexChanged.connect(self.refresh_table)
        top_bar.addWidget(self.combo_category)

        # Botón Exportar a CSV
        self.btn_export = QPushButton("Exportar CSV")
        self.btn_export.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_export.setStyleSheet("""
            QPushButton {
                background-color: rgba(16, 185, 129, 0.15);
                color: #34d399;
                border: 1px solid rgba(16, 185, 129, 0.4);
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(16, 185, 129, 0.25);
            }
        """)
        self.btn_export.clicked.connect(self._export_csv)
        top_bar.addWidget(self.btn_export)

        # Botón Confirmar Alerta Seleccionada
        self.btn_confirm = QPushButton("Confirmar Alerta")
        self.btn_confirm.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_confirm.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #f1f5f9;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #334155;
            }
        """)
        self.btn_confirm.clicked.connect(self._confirm_selected_event)
        top_bar.addWidget(self.btn_confirm)

        panel_layout.addLayout(top_bar)

        # -----------------------------------------------------------------
        # ZONA CENTRAL: Splitter Horizontal (Tabla a la izquierda + Panel Evidencia a la derecha)
        # -----------------------------------------------------------------
        content_splitter = QSplitter(Qt.Horizontal)
        content_splitter.setHandleWidth(8)

        # 1. Tabla de Eventos (8 Columnas)
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels([
            "ID", "Fecha / Hora", "Cámara", "Tipo de Evento", "Mensaje", "Prioridad", "Confirmación", "Evidencia"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.itemSelectionChanged.connect(self._on_table_selection_changed)
        self.table.cellDoubleClicked.connect(self._on_table_cell_double_clicked)
        content_splitter.addWidget(self.table)

        # 2. Panel Lateral de Evidencia Fotográfica
        evidence_panel = QFrame()
        evidence_panel.setMinimumWidth(300)
        evidence_panel.setMaximumWidth(400)
        evidence_panel.setStyleSheet("""
            QFrame {
                background-color: #0b1120;
                border: 1px solid #1e293b;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        ev_layout = QVBoxLayout(evidence_panel)
        ev_layout.setContentsMargins(10, 10, 10, 10)
        ev_layout.setSpacing(10)

        ev_header = QHBoxLayout()
        lbl_ev_title = QLabel("📷 Evidencia Fotográfica")
        lbl_ev_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #10b981;")
        ev_header.addWidget(lbl_ev_title)
        ev_header.addStretch()

        self.lbl_snap_badge = QLabel("SIN FOTO")
        self.lbl_snap_badge.setStyleSheet("background-color: #1e293b; color: #94a3b8; border-radius: 4px; padding: 2px 6px; font-size: 10px; font-family: monospace;")
        ev_header.addWidget(self.lbl_snap_badge)
        ev_layout.addLayout(ev_header)

        # Contenedor de la Imagen Preview
        self.lbl_preview = QLabel("Seleccione un evento del historial\npara examinar su captura fotográfica.")
        self.lbl_preview.setAlignment(Qt.AlignCenter)
        self.lbl_preview.setMinimumHeight(190)
        self.lbl_preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.lbl_preview.setStyleSheet("""
            background-color: #020617;
            border: 1px solid #334155;
            border-radius: 8px;
            color: #64748b;
            font-size: 11px;
        """)
        ev_layout.addWidget(self.lbl_preview)

        # Ficha de Información de la Evidencia
        self.lbl_meta_info = QLabel("Cámara: —\nFecha/Hora: —\nTipo: —")
        self.lbl_meta_info.setStyleSheet("color: #cbd5e1; font-size: 11px; line-height: 1.4;")
        ev_layout.addWidget(self.lbl_meta_info)

        # Botones de Acción sobre la Evidencia
        btn_box = QHBoxLayout()
        self.btn_inspect_full = QPushButton("🔍 Ampliar Imagen")
        self.btn_inspect_full.setEnabled(False)
        self.btn_inspect_full.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_inspect_full.setStyleSheet("""
            QPushButton {
                background-color: #064e3b;
                color: #34d399;
                border: 1px solid #059669;
                border-radius: 6px;
                padding: 6px 10px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #047857;
            }
            QPushButton:disabled {
                background-color: #1e293b;
                color: #64748b;
                border: 1px solid #334155;
            }
        """)
        self.btn_inspect_full.clicked.connect(self._open_full_snapshot)
        btn_box.addWidget(self.btn_inspect_full)

        self.btn_open_folder = QPushButton("📁 Ver Carpeta")
        self.btn_open_folder.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_open_folder.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #f1f5f9;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #334155;
            }
        """)
        self.btn_open_folder.clicked.connect(self._open_snapshots_folder)
        btn_box.addWidget(self.btn_open_folder)

        ev_layout.addLayout(btn_box)
        ev_layout.addStretch()

        content_splitter.addWidget(evidence_panel)
        content_splitter.setStretchFactor(0, 7)
        content_splitter.setStretchFactor(1, 3)

        panel_layout.addWidget(content_splitter)
        layout.addWidget(container)

    def refresh_table(self):
        cat_map = {
            0: "ALL",
            1: "Puerta",
            2: "Persona",
            3: "Vehículo",
            4: "Fallo",
            5: "Sistema"
        }
        category = cat_map.get(self.combo_category.currentIndex(), "ALL")
        search_txt = self.txt_search.text().strip()

        events = self.db.get_events(limit=100, category=category, search=search_txt)
        self.current_events = events

        prev_selected_id = self.selected_event["id"] if self.selected_event else None

        self.table.setRowCount(len(events))
        selected_row_to_restore = -1

        for row_idx, e in enumerate(events):
            if prev_selected_id and e["id"] == prev_selected_id:
                selected_row_to_restore = row_idx

            # ID
            item_id = QTableWidgetItem(f"#{e['id']}")
            item_id.setForeground(QColor("#64748b"))
            self.table.setItem(row_idx, 0, item_id)

            # Fecha/Hora
            item_time = QTableWidgetItem(e['timestamp'])
            item_time.setForeground(QColor("#cbd5e1"))
            self.table.setItem(row_idx, 1, item_time)

            # Cámara
            item_cam = QTableWidgetItem(e['camera'])
            item_cam.setForeground(QColor("#34d399"))
            self.table.setItem(row_idx, 2, item_cam)

            # Tipo de Evento
            item_type = QTableWidgetItem(e['event_type'])
            item_type.setForeground(QColor("#f1f5f9"))
            self.table.setItem(row_idx, 3, item_type)

            # Mensaje
            item_msg = QTableWidgetItem(e['message'])
            item_msg.setForeground(QColor("#cbd5e1"))
            self.table.setItem(row_idx, 4, item_msg)

            # Prioridad
            prio = e['priority']
            item_prio = QTableWidgetItem(prio)
            if prio == "Alta":
                item_prio.setForeground(QColor("#f87171"))
            elif prio == "Media":
                item_prio.setForeground(QColor("#fbbf24"))
            else:
                item_prio.setForeground(QColor("#94a3b8"))
            self.table.setItem(row_idx, 5, item_prio)

            # Confirmación
            is_conf = bool(e['confirmed'])
            conf_txt = f"Sí ({e.get('confirmed_by', 'Op')})" if is_conf else "Pendiente"
            item_conf = QTableWidgetItem(conf_txt)
            item_conf.setForeground(QColor("#10b981") if is_conf else QColor("#ef4444"))
            self.table.setItem(row_idx, 6, item_conf)

            # Evidencia Fotográfica (Snapshot)
            snap_path = e.get("snapshot_path")
            has_snap = bool(snap_path and os.path.exists(snap_path))
            item_ev = QTableWidgetItem("📷 Ver Foto" if has_snap else "—")
            item_ev.setTextAlignment(Qt.AlignCenter)
            item_ev.setForeground(QColor("#34d399") if has_snap else QColor("#64748b"))
            self.table.setItem(row_idx, 7, item_ev)

        if selected_row_to_restore >= 0:
            self.table.selectRow(selected_row_to_restore)

    def _on_table_selection_changed(self):
        curr_row = self.table.currentRow()
        if 0 <= curr_row < len(self.current_events):
            event = self.current_events[curr_row]
            self.selected_event = event
            self._update_evidence_panel(event)
        else:
            self.selected_event = None
            self._clear_evidence_panel()

    def _on_table_cell_double_clicked(self, row: int, col: int):
        if 0 <= row < len(self.current_events):
            event = self.current_events[row]
            snap_path = event.get("snapshot_path")
            if snap_path and os.path.exists(snap_path):
                self._open_full_snapshot()

    def _update_evidence_panel(self, event: dict):
        snap_path = event.get("snapshot_path")
        has_file = bool(snap_path and os.path.exists(snap_path))

        cam = event.get("camera", "Cámara")
        etype = event.get("event_type", "Alerta")
        ts = event.get("timestamp", "")
        prio = event.get("priority", "Media")
        msg = event.get("message", "")

        self.lbl_meta_info.setText(
            f"<b>Evento #{event.get('id')}</b><br>"
            f"<b>Cámara:</b> <span style='color:#34d399;'>{cam}</span><br>"
            f"<b>Tipo:</b> {etype} (Prioridad: {prio})<br>"
            f"<b>Fecha:</b> {ts}<br>"
            f"<b>Mensaje:</b> {msg}"
        )

        if has_file:
            self.lbl_snap_badge.setText("JPG DISPONIBLE")
            self.lbl_snap_badge.setStyleSheet("background-color: #064e3b; color: #34d399; border-radius: 4px; padding: 2px 6px; font-size: 10px; font-weight: bold;")
            pix = QPixmap(snap_path)
            if not pix.isNull():
                self.lbl_preview.setPixmap(pix.scaled(
                    320, 190,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                ))
            else:
                self.lbl_preview.setText("Error al cargar imagen.")
            self.btn_inspect_full.setEnabled(True)
        else:
            self.lbl_snap_badge.setText("SIN FOTO")
            self.lbl_snap_badge.setStyleSheet("background-color: #1e293b; color: #94a3b8; border-radius: 4px; padding: 2px 6px; font-size: 10px;")
            self.lbl_preview.setText("No hay captura fotográfica\nasociada a este evento.")
            self.btn_inspect_full.setEnabled(False)

    def _clear_evidence_panel(self):
        self.lbl_snap_badge.setText("SIN FOTO")
        self.lbl_snap_badge.setStyleSheet("background-color: #1e293b; color: #94a3b8; border-radius: 4px; padding: 2px 6px; font-size: 10px;")
        self.lbl_preview.setText("Seleccione un evento del historial\npara examinar su captura fotográfica.")
        self.lbl_meta_info.setText("Cámara: —\nFecha/Hora: —\nTipo: —")
        self.btn_inspect_full.setEnabled(False)

    def _open_full_snapshot(self):
        if not self.selected_event:
            return
        snap_path = self.selected_event.get("snapshot_path")
        if snap_path and os.path.exists(snap_path):
            dlg = SnapshotViewerDialog(snap_path, self.selected_event, parent=self)
            dlg.exec()

    def _open_snapshots_folder(self):
        sdir = get_snapshots_dir()
        try:
            if os.name == 'nt':
                os.startfile(str(sdir))
            else:
                subprocess.Popen(["xdg-open", str(sdir)])
        except Exception as e:
            QMessageBox.information(self, "Carpeta de Evidencias", f"Ruta de almacenamiento local:\n{sdir}")

    def _confirm_selected_event(self):
        curr_row = self.table.currentRow()
        if curr_row >= 0:
            id_item = self.table.item(curr_row, 0)
            if id_item:
                raw_id = id_item.text().replace("#", "").strip()
                if raw_id.isdigit():
                    self.db.confirm_event(int(raw_id), "Operador")
                    self.refresh_table()

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar Historial a CSV",
            f"VigiWinPro_AuditLogs_{int(datetime.now().timestamp())}.csv",
            "Archivos CSV (*.csv)"
        )
        if path:
            count = self.db.export_events_csv(path)
            QMessageBox.information(
                self,
                "Exportación Exitosa",
                f"Se han exportado {count} registros con evidencias correctamente a:\n{path}"
            )

    def apply_role_permissions(self, role: str):
        """Aplica restricciones dinámicas: Auditor no puede acusar alertas (solo lectura)."""
        can_confirm = role in ["Administrador", "Operador de Seguridad"]
        self.btn_confirm.setEnabled(can_confirm)
        if not can_confirm:
            self.btn_confirm.setToolTip("Restringido: El rol Auditor tiene acceso de solo lectura y no puede acusar alertas.")
        else:
            self.btn_confirm.setToolTip("")
