"""
VIGI-WIN PRO - Sistema de Estilos y Diseño QSS
Inspirado exactamente en el diseño de 'Backend vigiwin.html':
Gama Slate 950, acentos esmeralda (#10b981), paneles translúcidos glassmorphism y micro-animaciones.
"""

DARK_THEME_QSS = """
/* Reset y Ventana Principal */
QMainWindow, QWidget#centralWidget {
    background-color: #020617; /* slate-950 */
    color: #f8fafc;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 12px;
}

/* Encabezado Superior */
#topHeader {
    background-color: #0f172a; /* slate-900 */
    border-bottom: 1px solid #1e293b; /* slate-800 */
    min-height: 52px;
    max-height: 52px;
}

/* Barra Lateral Izquierda */
#sidebarPanel {
    background-color: #0b1120;
    border-right: 1px solid #1e293b;
    min-width: 210px;
    max-width: 230px;
}

/* Botones de Navegación Lateral */
QPushButton.nav-button {
    text-align: left;
    padding: 10px 14px;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 500;
    color: #94a3b8;
    background-color: transparent;
    border: 1px solid transparent;
}
QPushButton.nav-button:hover {
    background-color: rgba(30, 41, 59, 0.7);
    color: #e2e8f0;
}
QPushButton.nav-button:checked, QPushButton.nav-button-active {
    background-color: rgba(16, 185, 129, 0.12);
    color: #10b981; /* emerald-500 */
    border: 1px solid rgba(16, 185, 129, 0.3);
    font-weight: 600;
}

/* Paneles Contenedores Tipo Glass Panel */
QFrame.glass-panel {
    background-color: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 12px;
}

/* Botones Primarios Esmeralda */
QPushButton.btn-primary {
    background-color: #10b981;
    color: #020617;
    font-weight: bold;
    border-radius: 6px;
    padding: 7px 14px;
    border: none;
}
QPushButton.btn-primary:hover {
    background-color: #059669;
}
QPushButton.btn-primary:pressed {
    background-color: #047857;
}

/* Botones Secundarios Oscuros */
QPushButton.btn-secondary {
    background-color: #1e293b;
    color: #cbd5e1;
    font-weight: 500;
    border-radius: 6px;
    padding: 7px 14px;
    border: 1px solid #334155;
}
QPushButton.btn-secondary:hover {
    background-color: #334155;
    color: #ffffff;
}

/* Botones de Alerta / Simulación Ámbar y Rojos */
QPushButton.btn-amber {
    background-color: rgba(217, 119, 6, 0.2);
    color: #fcd34d;
    border: 1px solid rgba(245, 158, 11, 0.4);
    border-radius: 6px;
    padding: 7px 12px;
    font-weight: 500;
}
QPushButton.btn-amber:hover {
    background-color: rgba(217, 119, 6, 0.35);
}

QPushButton.btn-red {
    background-color: rgba(220, 38, 38, 0.2);
    color: #fca5a5;
    border: 1px solid rgba(239, 68, 68, 0.5);
    border-radius: 6px;
    padding: 7px 12px;
    font-weight: 500;
}
QPushButton.btn-red:hover {
    background-color: rgba(220, 38, 38, 0.35);
}

/* Tablas */
QTableWidget {
    background-color: #090e1a;
    border: 1px solid #1e293b;
    border-radius: 8px;
    gridline-color: #1e293b;
    color: #cbd5e1;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 11px;
}
QTableWidget::item {
    padding: 6px;
    border-bottom: 1px solid #1e293b;
}
QTableWidget::item:selected {
    background-color: rgba(16, 185, 129, 0.15);
    color: #10b981;
}
QHeaderView::section {
    background-color: #0f172a;
    color: #94a3b8;
    padding: 8px;
    border: none;
    border-bottom: 1px solid #1e293b;
    font-weight: bold;
    font-size: 11px;
}

/* Sliders */
QSlider::groove:horizontal {
    height: 4px;
    background: #1e293b;
    border-radius: 2px;
}
QSlider::sub-page:horizontal {
    background: #10b981;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #34d399;
    border: 2px solid #064e3b;
    width: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 7px;
}

/* Checkboxes y Switches */
QCheckBox {
    spacing: 8px;
    color: #e2e8f0;
    font-weight: 500;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #334155;
    background: #0f172a;
}
QCheckBox::indicator:checked {
    background: #10b981;
    border-color: #10b981;
    image: none;
}

/* Inputs de Texto y Selectores */
QLineEdit, QComboBox, QSpinBox {
    background-color: #090e1a;
    border: 1px solid #1e293b;
    border-radius: 6px;
    padding: 6px 10px;
    color: #f1f5f9;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #10b981;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox QAbstractItemView {
    background-color: #0f172a;
    border: 1px solid #1e293b;
    selection-background-color: #10b981;
    selection-color: #020617;
}

/* Barras de Desplazamiento */
QScrollBar:vertical {
    border: none;
    background: #090e1a;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #334155;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background: #10b981;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Visor de Código */
QPlainTextEdit#codeViewer {
    background-color: #020617;
    border: 1px solid #1e293b;
    border-radius: 6px;
    color: #cbd5e1;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 11px;
    line-height: 1.5;
}
"""
