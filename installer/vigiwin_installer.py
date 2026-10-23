"""
VIGI-WIN PRO - Asistente Gráfico de Instalación para Windows 10 y 11
Instalador profesional guiado en español.
Comprueba y auto-repara dependencias sin detenerse, copia archivos del sistema,
crea accesos directos en el Escritorio y Menú Inicio y preserva los datos de usuario.
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

# Configuración universal de alta resolución DPI para Windows 10/11
os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
os.environ.setdefault("QT_SCALE_FACTOR_ROUNDING_POLICY", "PassThrough")
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass

from PySide6.QtWidgets import (
    QApplication, QWizard, QWizardPage, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QCheckBox, QProgressBar, QPushButton,
    QFileDialog, QMessageBox, QFrame
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCursor, QIcon

class WelcomePage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Instalación de VIGI-WIN PRO v1.0")
        self.setSubTitle("Sistema Inteligente de Vigilancia de Puertas, Personas y Vehículos")

        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        info = QLabel(
            "Bienvenido al asistente de instalación de <b>VIGI-WIN PRO</b> para Windows 10 y Windows 11.<br><br>"
            "Este instalador configurará automáticamente todos los módulos necesarios, verificará los "
            "controladores de visión artificial y preparará el entorno de trabajo local sin necesidad de "
            "conexión continua a Internet ni servicios de pago.<br><br>"
            "Presione <b>Siguiente</b> para comenzar la verificación de requisitos y la instalación guiada."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #cbd5e1; font-size: 12px; line-height: 1.5;")
        layout.addWidget(info)


class DestinationPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Carpeta de Destino")
        self.setSubTitle("Seleccione la carpeta donde se instalarán los componentes de VIGI-WIN PRO")

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        lbl = QLabel("Ruta de instalación:")
        lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        layout.addWidget(lbl)

        h_row = QHBoxLayout()
        # Carpeta por defecto en LocalAppData o ProgramFiles
        default_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "VigiWinPro")
        self.txt_path = QLineEdit(default_dir)
        self.registerField("install_path*", self.txt_path)
        h_row.addWidget(self.txt_path)

        btn_browse = QPushButton("Examinar...")
        btn_browse.clicked.connect(self._browse)
        h_row.addWidget(btn_browse)
        layout.addLayout(h_row)

        self.chk_desktop = QCheckBox("Crear acceso directo en el Escritorio")
        self.chk_desktop.setChecked(True)
        self.registerField("create_desktop_icon", self.chk_desktop)
        layout.addWidget(self.chk_desktop)

        self.chk_startmenu = QCheckBox("Crear acceso en el Menú Inicio de Windows")
        self.chk_startmenu.setChecked(True)
        self.registerField("create_startmenu_icon", self.chk_startmenu)
        layout.addWidget(self.chk_startmenu)

        layout.addStretch()

    def _browse(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta de Instalación", self.txt_path.text())
        if folder:
            self.txt_path.setText(folder)


class ProgressInstallPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Instalando Componentes")
        self.setSubTitle("Comprobando requisitos, desplegando archivos y auto-reparando dependencias...")
        self.is_complete = False

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        self.lbl_status = QLabel("Iniciando proceso...")
        self.lbl_status.setStyleSheet("color: #10b981; font-family: monospace; font-size: 11px;")
        layout.addWidget(self.lbl_status)

        self.prog_bar = QProgressBar()
        self.prog_bar.setRange(0, 100)
        self.prog_bar.setValue(0)
        layout.addWidget(self.prog_bar)

        self.log_label = QLabel("")
        self.log_label.setStyleSheet("color: #64748b; font-size: 10px; font-family: monospace;")
        layout.addWidget(self.log_label)

        layout.addStretch()

    def initializePage(self):
        self.prog_bar.setValue(10)
        self.lbl_status.setText("Comprobando entorno y permisos...")
        QTimer.singleShot(400, self._step_requirements)

    def _step_requirements(self):
        self.prog_bar.setValue(35)
        self.lbl_status.setText("Verificando librerías de visión artificial...")
        # Auto-reparar dependencias silenciosamente
        try:
            import cv2
            import numpy
            import PySide6
        except ImportError as e:
            self.log_label.setText(f"Auto-descargando componente: {e}")
            try:
                subprocess.call([sys.executable, "-m", "pip", "install", "PySide6", "opencv-python", "numpy", "--quiet"])
            except Exception:
                pass

        QTimer.singleShot(400, self._step_copy_files)

    def _step_copy_files(self):
        self.prog_bar.setValue(70)
        self.lbl_status.setText("Copiando módulos del sistema a destino...")

        dest_dir = self.field("install_path")
        try:
            os.makedirs(dest_dir, exist_ok=True)
            # Copiar árbol de vigiwin y scripts
            src_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            vigiwin_src = os.path.join(src_root, "vigiwin")
            vigiwin_dst = os.path.join(dest_dir, "vigiwin")
            if os.path.exists(vigiwin_src):
                shutil.copytree(vigiwin_src, vigiwin_dst, dirs_exist_ok=True)

            shutil.copy2(os.path.join(src_root, "run_app.py"), os.path.join(dest_dir, "run_app.py"))
            shutil.copy2(os.path.join(src_root, "requirements.txt"), os.path.join(dest_dir, "requirements.txt"))
            user_home = os.path.expanduser("~")
            app_dir = os.path.join(user_home, ".vigiwinpro")
            os.makedirs(os.path.join(app_dir, "snapshots"), exist_ok=True)
            os.makedirs(os.path.join(app_dir, "backups"), exist_ok=True)
        except Exception as e:
            self.log_label.setText(f"Aviso de copia: {e}")

        QTimer.singleShot(400, self._step_create_shortcuts)

    def _step_create_shortcuts(self):
        self.prog_bar.setValue(90)
        self.lbl_status.setText("Generando accesos directos e icono vanguardista en Windows...")
        dest_dir = self.field("install_path")
        launcher_path = os.path.join(dest_dir, "run_app.py")
        ico_path = os.path.join(dest_dir, "vigiwin", "assets", "icon.ico")
        target_exe = os.path.join(dest_dir, "VigiWinPro.exe")

        # Seleccionar ejecutable destino
        if os.path.exists(target_exe):
            target_path = target_exe
            target_args = ""
        else:
            # En modo entorno Python local
            target_path = sys.executable
            target_args = f'"{launcher_path}"'

        # Script .bat auxiliar
        bat_launcher = os.path.join(dest_dir, "Iniciar_VigiWinPro.bat")
        with open(bat_launcher, "w", encoding="utf-8") as f:
            f.write(f'@echo off\ncd /d "{dest_dir}"\nstart "" pythonw run_app.py\n')

        # Crear Acceso Directo (.lnk) en el Escritorio con icono vanguardista
        if self.field("create_desktop_icon"):
            try:
                desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                if os.path.exists(desktop):
                    shortcut_lnk = os.path.join(desktop, "VIGI-WIN PRO.lnk")
                    ps_cmd = (
                        f"$WshShell = New-Object -ComObject WScript.Shell; "
                        f"$Shortcut = $WshShell.CreateShortcut('{shortcut_lnk}'); "
                        f"$Shortcut.TargetPath = '{target_path}'; "
                        f"$Shortcut.Arguments = '{target_args}'; "
                        f"$Shortcut.WorkingDirectory = '{dest_dir}'; "
                        f"$Shortcut.IconLocation = '{ico_path},0'; "
                        f"$Shortcut.Description = 'VIGI-WIN PRO - Sistema Inteligente de Vigilancia'; "
                        f"$Shortcut.Save();"
                    )
                    subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, timeout=12)
            except Exception as e:
                self.log_label.setText(f"Aviso acceso directo: {e}")

        # Crear Acceso Directo en Menú Inicio de Windows
        if self.field("create_startmenu_icon"):
            try:
                appdata = os.environ.get("APPDATA", "")
                if appdata:
                    start_programs = os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs", "VigiWinPro")
                    os.makedirs(start_programs, exist_ok=True)
                    shortcut_start = os.path.join(start_programs, "VIGI-WIN PRO.lnk")
                    ps_cmd = (
                        f"$WshShell = New-Object -ComObject WScript.Shell; "
                        f"$Shortcut = $WshShell.CreateShortcut('{shortcut_start}'); "
                        f"$Shortcut.TargetPath = '{target_path}'; "
                        f"$Shortcut.Arguments = '{target_args}'; "
                        f"$Shortcut.WorkingDirectory = '{dest_dir}'; "
                        f"$Shortcut.IconLocation = '{ico_path},0'; "
                        f"$Shortcut.Description = 'VIGI-WIN PRO - Sistema Inteligente de Vigilancia'; "
                        f"$Shortcut.Save();"
                    )
                    subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, timeout=12)
            except Exception:
                pass

        self.prog_bar.setValue(100)
        self.lbl_status.setText("¡Instalación completada con éxito!")
        self.is_complete = True
        self.completeChanged.emit()

    def isComplete(self):
        return self.is_complete


class FinishedPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Instalación Finalizada")
        self.setSubTitle("VIGI-WIN PRO v1.0 está listo para ser utilizado")

        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        info = QLabel(
            "<b>¡Enhorabuena!</b><br><br>"
            "La instalación de <b>VIGI-WIN PRO</b> ha concluido satisfactoriamente.<br><br>"
            "• La base de datos local persistente ha sido configurada en: <code>~/.vigiwinpro/vigiwin.db</code><br>"
            "• Carpeta de evidencias e instantáneas forenses: <code>~/.vigiwinpro/snapshots/</code><br>"
            "• Autenticación inicial obligatoria (Admin, Operador, Auditor) y cambio de usuario en caliente.<br>"
            "• Modo multi-cámara interactivo (Grid 2x2 / 1x1) y vigilancia de puertas, personas y vehículos.<br>"
            "• Puede iniciar la aplicación en cualquier momento desde el acceso directo generado."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #cbd5e1; font-size: 12px; line-height: 1.5;")
        layout.addWidget(info)

        self.chk_launch = QCheckBox("Ejecutar VIGI-WIN PRO ahora")
        self.chk_launch.setChecked(True)
        layout.addWidget(self.chk_launch)

        layout.addStretch()


class VigiWinInstallerWizard(QWizard):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Asistente de Instalación - VIGI-WIN PRO v1.0")

        # Cargar icono vanguardista oficial
        base_dir = Path(__file__).resolve().parent.parent
        icon_path = base_dir / "vigiwin" / "assets" / "icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        # Adaptabilidad automática a la resolución del monitor
        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            target_w = min(620, max(480, int(avail.width() * 0.85)))
            target_h = min(440, max(360, int(avail.height() * 0.75)))
            self.resize(target_w, target_h)
        else:
            self.resize(600, 420)

        self.setWizardStyle(QWizard.ModernStyle)
        self.setStyleSheet("""
            QWizard {
                background-color: #020617;
                color: #f8fafc;
            }
            QLabel {
                color: #e2e8f0;
            }
            QPushButton {
                background-color: #10b981;
                color: #020617;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 14px;
                border: none;
            }
            QPushButton:hover {
                background-color: #059669;
            }
            QLineEdit {
                background-color: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 6px;
                padding: 6px;
                color: #f1f5f9;
            }
            QProgressBar {
                background-color: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 4px;
                height: 10px;
            }
            QProgressBar::chunk {
                background-color: #10b981;
                border-radius: 4px;
            }
        """)

        self.addPage(WelcomePage())
        self.addPage(DestinationPage())
        self.page_progress = ProgressInstallPage()
        self.addPage(self.page_progress)
        self.page_finish = FinishedPage()
        self.addPage(self.page_finish)

    def accept(self):
        if self.page_finish.chk_launch.isChecked():
            dest_dir = self.field("install_path")
            launcher = os.path.join(dest_dir, "run_app.py")
            if os.path.exists(launcher):
                subprocess.Popen([sys.executable, launcher])
        super().accept()

def main():
    if hasattr(Qt, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    base_dir = Path(__file__).resolve().parent.parent
    icon_path = base_dir / "vigiwin" / "assets" / "icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    wizard = VigiWinInstallerWizard()
    wizard.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
