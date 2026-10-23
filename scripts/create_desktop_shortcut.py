"""
VIGI-WIN PRO - Generador y Actualizador de Acceso Directo de Escritorio
Configura el acceso directo en el Escritorio de Windows 10/11 con el icono vanguardista oficial.
"""
import os
import sys
import subprocess
from pathlib import Path

def create_desktop_shortcut():
    project_root = Path(__file__).resolve().parent.parent
    icon_path = project_root / "vigiwin" / "assets" / "icon.ico"
    exe_dist = project_root / "dist" / "VigiWinPro" / "VigiWinPro.exe"
    run_app_py = project_root / "run_app.py"

    if exe_dist.exists():
        target_path = str(exe_dist)
        target_args = ""
        work_dir = str(exe_dist.parent)
    else:
        target_path = sys.executable
        target_args = f'"{run_app_py}"'
        work_dir = str(project_root)

    # Obtener la ruta del Escritorio de Windows
    desktop = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"
    if not desktop.exists():
        # Fallback OneDrive Desktop si está sincronizado
        onedrive_desktop = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "OneDrive" / "Desktop"
        if onedrive_desktop.exists():
            desktop = onedrive_desktop

    shortcut_lnk = desktop / "VIGI-WIN PRO.lnk"

    # Comando PowerShell con WScript.Shell
    ps_cmd = f"""
    $wsh = New-Object -ComObject WScript.Shell;
    $s = $wsh.CreateShortcut('{str(shortcut_lnk)}');
    $s.TargetPath = '{target_path}';
    $s.Arguments = '{target_args}';
    $s.WorkingDirectory = '{work_dir}';
    $s.IconLocation = '{str(icon_path)},0';
    $s.Description = 'VIGI-WIN PRO - Sistema Inteligente de Vigilancia de Puertas, Personas y Vehículos';
    $s.Save();
    """

    res = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_cmd],
        capture_output=True,
        text=True,
        timeout=15
    )

    if res.returncode == 0 and shortcut_lnk.exists():
        print(f"Acceso directo generado exitosamente en: {shortcut_lnk}")
        print(f"Target: {target_path}")
        print(f"Icon: {icon_path}")
        return True
    else:
        print(f"Error al generar acceso directo: {res.stderr}")
        return False

if __name__ == "__main__":
    create_desktop_shortcut()
