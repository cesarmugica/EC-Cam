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
; No relanzar por su cuenta lo que cerró: [Run] arranca el servicio una sola vez.
RestartApplications=no

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "autostart"; Description: "Iniciar el servidor EC-Cam al encender Windows (recomendado)"; GroupDescription: "Servidor:"
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; GroupDescription: "Accesos directos:"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
; El acceso del escritorio se llamaba "Iniciar EC-Cam" (1.1.3 a 1.1.10); ahora es "EC-Cam".
Type: files; Name: "{userdesktop}\Iniciar EC-Cam.lnk"

[Icons]
Name: "{group}\Iniciar EC-Cam"; Filename: "{app}\eccam-server.exe"; Comment: "Inicia el servicio EC-Cam y abre tus cámaras"
Name: "{group}\Detener servicio EC-Cam"; Filename: "{sys}\taskkill.exe"; Parameters: "/IM eccam-server.exe /F"; IconFilename: "{app}\eccam-server.exe"
Name: "{group}\Carpeta de datos de EC-Cam"; Filename: "{localappdata}\EC-Cam"
Name: "{group}\Desinstalar EC-Cam"; Filename: "{uninstallexe}"
Name: "{userdesktop}\EC-Cam"; Filename: "{app}\eccam-server.exe"; Tasks: desktopicon
Name: "{userstartup}\Servicio EC-Cam"; Filename: "{app}\eccam-server.exe"; Parameters: "--no-browser"; Tasks: autostart

[Run]
; Siempre arrancar el servicio al terminar (antes dependía de una casilla).
Filename: "{app}\eccam-server.exe"; Flags: nowait skipifsilent

[Registry]
; Enlace eccam:// para el botón "Iniciar EC-Cam" de la página (por usuario, sin admin).
Root: HKCU; Subkey: "Software\Classes\eccam"; ValueType: string; ValueName: ""; ValueData: "URL:EC-Cam"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\eccam"; ValueType: string; ValueName: "URL Protocol"; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\eccam\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\eccam-server.exe,0"
Root: HKCU; Subkey: "Software\Classes\eccam\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\eccam-server.exe"" --no-browser"

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
