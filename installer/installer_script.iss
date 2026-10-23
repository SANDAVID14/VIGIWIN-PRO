; =====================================================================
; VIGI-WIN PRO v1.0 - Script de Instalador Inno Setup para Windows 10/11
; =====================================================================

[Setup]
AppId={{9F82A4D1-1C2E-4A7B-9E31-7B8C0D4F5A21}
AppName=VIGI-WIN PRO
AppVersion=1.0
AppVerName=VIGI-WIN PRO v1.0
AppPublisher=VigiWinPro
DefaultDirName={autopf}\VigiWinPro
DefaultGroupName=VIGI-WIN PRO
AllowNoIcons=yes
OutputDir=..\installer_output
OutputBaseFilename=VigiWinPro_Instalador_v1.0_Windows
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\VigiWinPro\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\VIGI-WIN PRO"; Filename: "{app}\VigiWinPro.exe"
Name: "{group}\Desinstalar VIGI-WIN PRO"; Filename: "{uninstallexe}"
Name: "{autodesktop}\VIGI-WIN PRO"; Filename: "{app}\VigiWinPro.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\VigiWinPro.exe"; Description: "{cm:LaunchProgram,VIGI-WIN PRO}"; Flags: nowait postinstall skipifsilent
