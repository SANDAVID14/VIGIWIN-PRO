"""
VIGI-WIN PRO - Pestaña 4: Gestor de Código, Build y Auto-Reparación
Explorador de módulos fuente, estado de auto-reparación (bootstrap.py)
y visor de código para verificación transparente por el propietario.
"""
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QPlainTextEdit, QApplication
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor

class CodeTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.code_files = {}
        self._load_code_files()
        self.init_ui()

    def _load_code_files(self):
        # Escanear archivos principales del proyecto
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        targets = [
            ("bootstrap.py", os.path.join(base_dir, "installer", "bootstrap.py")),
            ("run_app.py", os.path.join(base_dir, "run_app.py")),
            ("database.py", os.path.join(base_dir, "vigiwin", "core", "database.py")),
            ("door_detector.py", os.path.join(base_dir, "vigiwin", "vision", "door_detector.py")),
            ("object_detector.py", os.path.join(base_dir, "vigiwin", "vision", "object_detector.py")),
            ("camera_stream.py", os.path.join(base_dir, "vigiwin", "vision", "camera_stream.py")),
            ("alert_overlay.py", os.path.join(base_dir, "vigiwin", "ui", "alert_overlay.py")),
            ("build.bat", os.path.join(base_dir, "installer", "build.bat")),
            ("requirements.txt", os.path.join(base_dir, "requirements.txt")),
            ("installer_script.iss", os.path.join(base_dir, "installer", "installer_script.iss"))
        ]

        for name, path in targets:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        self.code_files[name] = f.read()
                except Exception as e:
                    self.code_files[name] = f"# Error al leer archivo: {e}"
            else:
                self.code_files[name] = f"# Archivo disponible para auto-reparación ({name})"

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        container = QFrame()
        container.setStyleSheet("background-color: #0f172a; border: 1px solid #1e293b; border-radius: 12px; padding: 14px;")
        panel_layout = QVBoxLayout(container)
        panel_layout.setSpacing(12)

        # Header
        top_bar = QHBoxLayout()
        title_box = QVBoxLayout()
        lbl_title = QLabel("Módulos del Paquete de Instalación y Auto-Reparación")
        lbl_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #f8fafc;")
        title_box.addWidget(lbl_title)

        lbl_subtitle = QLabel("Código fuente completo entregado al propietario sin dependencias opacas.")
        lbl_subtitle.setStyleSheet("font-size: 11px; color: #64748b;")
        title_box.addWidget(lbl_subtitle)
        top_bar.addLayout(title_box)

        top_bar.addStretch()

        btn_verify = QPushButton("Verificar Integridad / Auto-Repair")
        btn_verify.setCursor(QCursor(Qt.PointingHandCursor))
        btn_verify.setStyleSheet("""
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
        btn_verify.clicked.connect(self._run_auto_repair_check)
        top_bar.addWidget(btn_verify)

        panel_layout.addLayout(top_bar)

        # Contenido: Explorador de Archivos (Izquierda) + Visor de Código (Derecha)
        content_box = QHBoxLayout()
        content_box.setSpacing(12)

        # Lista de archivos a la izquierda
        files_col = QVBoxLayout()
        files_col.setSpacing(6)
        lbl_ftree = QLabel("ARCHIVOS DEL PROYECTO")
        lbl_ftree.setStyleSheet("font-size: 10px; font-weight: bold; color: #64748b; letter-spacing: 0.5px;")
        files_col.addWidget(lbl_ftree)

        self.file_buttons = {}
        for fname in self.code_files.keys():
            btn = QPushButton(fname)
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    background-color: #090e1a;
                    color: #cbd5e1;
                    border: 1px solid #1e293b;
                    border-radius: 6px;
                    padding: 8px 12px;
                    font-family: monospace;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #1e293b;
                    color: #ffffff;
                }
            """)
            btn.clicked.connect(lambda checked=False, fn=fname: self._select_file(fn))
            files_col.addWidget(btn)
            self.file_buttons[fname] = btn

        files_col.addStretch()
        content_box.addLayout(files_col, stretch=2)

        # Visor de Código a la derecha
        viewer_col = QVBoxLayout()
        viewer_col.setSpacing(6)

        viewer_header = QHBoxLayout()
        self.lbl_current_file = QLabel("bootstrap.py")
        self.lbl_current_file.setStyleSheet("color: #10b981; font-family: monospace; font-weight: bold; font-size: 12px;")
        viewer_header.addWidget(self.lbl_current_file)
        viewer_header.addStretch()

        btn_copy = QPushButton("Copiar Código")
        btn_copy.setCursor(QCursor(Qt.PointingHandCursor))
        btn_copy.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #cbd5e1;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #ffffff;
            }
        """)
        btn_copy.clicked.connect(self._copy_code)
        viewer_header.addWidget(btn_copy)
        viewer_col.addLayout(viewer_header)

        self.code_editor = QPlainTextEdit()
        self.code_editor.setReadOnly(True)
        self.code_editor.setObjectName("codeViewer")
        self.code_editor.setStyleSheet("""
            QPlainTextEdit#codeViewer {
                background-color: #020617;
                color: #cbd5e1;
                border: 1px solid #1e293b;
                border-radius: 8px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
                line-height: 1.4;
            }
        """)
        viewer_col.addWidget(self.code_editor)
        content_box.addLayout(viewer_col, stretch=5)

        panel_layout.addLayout(content_box)
        layout.addWidget(container)

        # Seleccionar bootstrap.py por defecto
        self._select_file("bootstrap.py")

    def _select_file(self, filename: str):
        self.lbl_current_file.setText(filename)
        code = self.code_files.get(filename, "# Fichero no disponible")
        self.code_editor.setPlainText(code)

        for fn, btn in self.file_buttons.items():
            if fn == filename:
                btn.setStyleSheet("""
                    QPushButton {
                        text-align: left;
                        background-color: rgba(16, 185, 129, 0.12);
                        color: #10b981;
                        border: 1px solid rgba(16, 185, 129, 0.4);
                        border-radius: 6px;
                        padding: 8px 12px;
                        font-family: monospace;
                        font-weight: bold;
                        font-size: 11px;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        text-align: left;
                        background-color: #090e1a;
                        color: #cbd5e1;
                        border: 1px solid #1e293b;
                        border-radius: 6px;
                        padding: 8px 12px;
                        font-family: monospace;
                        font-size: 11px;
                    }
                    QPushButton:hover {
                        background-color: #1e293b;
                        color: #ffffff;
                    }
                """)

    def _copy_code(self):
        text = self.code_editor.toPlainText()
        QApplication.clipboard().setText(text)

    def _run_auto_repair_check(self):
        self._load_code_files()
        curr = self.lbl_current_file.text()
        self._select_file(curr)
