; ============================================================
;  EC-Cam — instalador de Windows (Inno Setup 6)
;  Se compila con windows\build.ps1 (pasa AppVersion y SourceDir).
;  Instala por usuario (no pide permisos de administrador).
; ============================================================
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#ifndef SourceDir
  #define SourceDir "dist\eccam-server"
#endif

[Setup]
AppId={{6E7C2B1A-4F3D-4C8E-9A51-EC0CAA0F1E01}
AppName=EC-Cam
AppVersion={#AppVersion}
AppVerName=EC-Cam {#AppVersion}
AppPublisher=EC-Cam
DefaultDirName={localappdata}\Programs\EC-Cam
DefaultGroupName=EC-Cam
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputBaseFilename=EC-Cam-Setup-{#AppVersion}
SetupIconFile=..\web\img\eccam.ico
UninstallDisplayIcon={app}\eccam-server.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=force

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "autostart"; Description: "Iniciar el servidor EC-Cam al encender Windows (recomendado)"; GroupDescription: "Servidor:"
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; GroupDescription: "Accesos directos:"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\EC-Cam"; Filename: "{app}\eccam-server.exe"; Comment: "Inicia el servidor y abre EC-Cam"
Name: "{group}\Detener servidor EC-Cam"; Filename: "{sys}\taskkill.exe"; Parameters: "/IM eccam-server.exe /F"; IconFilename: "{app}\eccam-server.exe"
Name: "{group}\Carpeta de datos de EC-Cam"; Filename: "{localappdata}\EC-Cam"
Name: "{group}\Desinstalar EC-Cam"; Filename: "{uninstallexe}"
Name: "{userdesktop}\EC-Cam"; Filename: "{app}\eccam-server.exe"; Tasks: desktopicon
Name: "{userstartup}\EC-Cam servidor"; Filename: "{app}\eccam-server.exe"; Parameters: "--no-browser"; Tasks: autostart

[Run]
Filename: "{app}\eccam-server.exe"; Description: "Iniciar EC-Cam ahora"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{sys}\taskkill.exe"; Parameters: "/IM eccam-server.exe /F"; Flags: runhidden; RunOnceId: "StopEcCam"

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var R: Integer;
begin
  { Detener una versión anterior antes de copiar archivos }
  if CurStep = ssInstall then
    Exec(ExpandConstant('{sys}\taskkill.exe'), '/IM eccam-server.exe /F', '', SW_HIDE, ewWaitUntilTerminated, R);
end;
