[Setup]
AppName=密盾 AegisVault
AppVersion=3.0
AppPublisher=AegisVault
DefaultDirName={autopf}\AegisVault
DefaultGroupName=密盾 AegisVault
UninstallDisplayIcon={app}\AegisVault.exe
OutputDir=output
OutputBaseFilename=AegisVault_Setup_v3.0
Compression=lzma2
SolidCompression=yes
SetupIconFile=app.ico
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
WizardStyle=modern

[Files]
Source: "dist\AegisVault\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autodesktop}\密盾 AegisVault"; Filename: "{app}\AegisVault.exe"; Comment: "密盾账号管理工具"
Name: "{group}\密盾 AegisVault"; Filename: "{app}\AegisVault.exe"
Name: "{group}\卸载 密盾"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\AegisVault.exe"; Description: "立即启动 密盾 AegisVault"; Flags: nowait postinstall skipifsilent
