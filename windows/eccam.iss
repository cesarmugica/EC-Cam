; ============================================================
;  EC-Cam — instalador de Windows (Inno Setup 6)
;  Se compila con windows\build.ps1 (pasa AppVersion y SourceDir).
;  Instala por usuario (no pide permisos de administrador).
; ============================================================
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#ifndef SourceDir
  #define SourceDir "dist\eccam"
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
SetupIconFile=..\src\web\img\eccam.ico
UninstallDisplayIcon={app}\app\web\img\eccam.ico
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
Name: "en"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
es.TaskAutostart=Iniciar el servicio EC-Cam al encender Windows (recomendado)
en.TaskAutostart=Start the EC-Cam service when Windows starts (recommended)
es.GroupService=Servicio:
en.GroupService=Service:
es.TaskDesktop=Crear acceso directo «EC-Cam» en el escritorio
en.TaskDesktop=Create an "EC-Cam" desktop shortcut
es.GroupShortcuts=Accesos directos:
en.GroupShortcuts=Shortcuts:
es.IconStart=Iniciar EC-Cam
en.IconStart=Start EC-Cam
es.IconStartComment=Inicia el servicio EC-Cam y abre tus cámaras
en.IconStartComment=Starts the EC-Cam service and opens your cameras
es.IconStop=Detener servicio EC-Cam
en.IconStop=Stop EC-Cam service
es.IconData=Carpeta de datos de EC-Cam
en.IconData=EC-Cam data folder
es.IconUninstall=Desinstalar EC-Cam
en.IconUninstall=Uninstall EC-Cam

[Tasks]
Name: "autostart"; Description: "{cm:TaskAutostart}"; GroupDescription: "{cm:GroupService}"
Name: "desktopicon"; Description: "{cm:TaskDesktop}"; GroupDescription: "{cm:GroupShortcuts}"

; Desde la 2.3.0 EC-Cam corre con el Python oficial firmado (python\pythonw.exe)
; y su código en app\. Ya no hay eccam-server.exe (Windows 11 lo bloqueaba).
#define Py "{app}\python\pythonw.exe"
#define Ico "{app}\app\web\img\eccam.ico"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
; El acceso del escritorio se llamaba "Iniciar EC-Cam" (1.1.3 a 1.1.10); ahora es "EC-Cam".
Type: files; Name: "{userdesktop}\Iniciar EC-Cam.lnk"
; Los accesos del menú Inicio cambian de nombre según el idioma: limpiar los anteriores.
Type: files; Name: "{group}\*.lnk"
; Versiones anteriores (compiladas con PyInstaller)
Type: files; Name: "{app}\eccam-server.exe"
Type: files; Name: "{app}\ffmpeg.exe"
Type: filesandordirs; Name: "{app}\_internal"
Type: filesandordirs; Name: "{app}\app"

[Icons]
Name: "{group}\{cm:IconStart}"; Filename: "{#Py}"; Parameters: """{app}\app\eccam_server.py"""; WorkingDir: "{app}"; IconFilename: "{#Ico}"; Comment: "{cm:IconStartComment}"
Name: "{group}\{cm:IconStop}"; Filename: "{#Py}"; Parameters: """{app}\app\eccam_server.py"" --stop"; WorkingDir: "{app}"; IconFilename: "{#Ico}"
Name: "{group}\{cm:IconData}"; Filename: "{localappdata}\EC-Cam"
Name: "{group}\{cm:IconUninstall}"; Filename: "{uninstallexe}"
Name: "{userdesktop}\EC-Cam"; Filename: "{#Py}"; Parameters: """{app}\app\eccam_server.py"""; WorkingDir: "{app}"; IconFilename: "{#Ico}"; Tasks: desktopicon
Name: "{userstartup}\Servicio EC-Cam"; Filename: "{#Py}"; Parameters: """{app}\app\eccam_server.py"" --no-browser"; WorkingDir: "{app}"; IconFilename: "{#Ico}"; Tasks: autostart

[Run]
; Siempre arrancar el servicio al terminar (antes dependía de una casilla).
Filename: "{#Py}"; Parameters: """{app}\app\eccam_server.py"""; WorkingDir: "{app}"; Flags: nowait skipifsilent

[Registry]
; Enlace eccam:// para el botón "Iniciar EC-Cam" de la página (por usuario, sin admin).
Root: HKCU; Subkey: "Software\Classes\eccam"; ValueType: string; ValueName: ""; ValueData: "URL:EC-Cam"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\eccam"; ValueType: string; ValueName: "URL Protocol"; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\eccam\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{#Ico}"
Root: HKCU; Subkey: "Software\Classes\eccam\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\python\pythonw.exe"" ""{app}\app\eccam_server.py"" --no-browser"

[UninstallRun]
Filename: "{#Py}"; Parameters: """{app}\app\eccam_server.py"" --stop"; Flags: runhidden waituntilterminated; RunOnceId: "StopEcCam"

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var R: Integer;
begin
  { Detener una versión anterior antes de copiar archivos }
  if CurStep = ssInstall then
  begin
    { 2.3.0 o más nueva: pedirle al servicio que se cierre }
    if FileExists(ExpandConstant('{app}\python\pythonw.exe')) then
      Exec(ExpandConstant('{app}\python\pythonw.exe'), '"' + ExpandConstant('{app}\app\eccam_server.py') + '" --stop', ExpandConstant('{app}'), SW_HIDE, ewWaitUntilTerminated, R);
    { Versiones anteriores (eccam-server.exe) }
    Exec(ExpandConstant('{sys}\taskkill.exe'), '/IM eccam-server.exe /F', '', SW_HIDE, ewWaitUntilTerminated, R);
    Sleep(800);
  end;
  { El idioma del instalador es el idioma inicial de la app (luego se cambia en la app) }
  if CurStep = ssPostInstall then
  begin
    ForceDirectories(ExpandConstant('{localappdata}\EC-Cam'));
    SaveStringToFile(ExpandConstant('{localappdata}\EC-Cam\language.txt'), ActiveLanguage, False);
  end;
end;
