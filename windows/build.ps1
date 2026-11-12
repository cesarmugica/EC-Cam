# ============================================================
#  EC-Cam — genera el instalador de Windows
#  Requisitos: Inno Setup 6 (jrsoftware.org/isinfo.php). Python y FFmpeg
#  se descargan solos (Python "embeddable" oficial de python.org).
#  Uso (desde la carpeta eccam):
#    powershell -ExecutionPolicy Bypass -File .\windows\build.ps1
#  Resultado: windows\out\EC-Cam-Setup-<versión>.exe
# ============================================================
$ErrorActionPreference = 'Stop'
$scriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = (Resolve-Path (Join-Path $scriptDir '..')).Path
$srcRoot     = Join-Path $projectRoot 'src'
$ffmpegUrl   = if ($env:ECCAM_FFMPEG_URL) { $env:ECCAM_FFMPEG_URL } else { 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' }

function Invoke-Checked([string]$FilePath, [string[]]$ArgumentList = @()) {
  & $FilePath @ArgumentList
  if ($LASTEXITCODE -ne 0) { throw "$FilePath terminó con código $LASTEXITCODE" }
}

# --- versión (de eccam_server.py) ---
$version = (Select-String -Path (Join-Path $srcRoot 'eccam_server.py') -Pattern '^APP_VERSION = "(.+)"').Matches[0].Groups[1].Value
Write-Host "EC-Cam $version" -ForegroundColor Cyan

$distDir = Join-Path $scriptDir 'dist'
$outDir  = Join-Path $scriptDir 'out'
$appRoot = Join-Path $distDir 'eccam'          # lo que instala Inno Setup
$pyDir   = Join-Path $appRoot 'python'          # Python oficial (firmado)
$appDir  = Join-Path $appRoot 'app'             # código de EC-Cam
if (Test-Path $appRoot) { Remove-Item $appRoot -Recurse -Force }
New-Item -ItemType Directory -Force -Path $distDir, $outDir, $pyDir, $appDir | Out-Null

# --- FFmpeg (se descarga una vez y se reutiliza) ---
$ffmpegCache = Join-Path $scriptDir 'ffmpeg.exe'
if (-not (Test-Path $ffmpegCache)) {
  $tmp = Join-Path ([IO.Path]::GetTempPath()) ("eccam-ffmpeg-" + [guid]::NewGuid().ToString('N'))
  try {
    New-Item -ItemType Directory -Force -Path $tmp | Out-Null
    Write-Host 'Descargando FFmpeg...'
    Invoke-WebRequest -Uri $ffmpegUrl -OutFile (Join-Path $tmp 'ffmpeg.zip')
    Expand-Archive -Path (Join-Path $tmp 'ffmpeg.zip') -DestinationPath (Join-Path $tmp 'x') -Force
    $bin = Get-ChildItem -Path (Join-Path $tmp 'x') -Filter ffmpeg.exe -Recurse | Select-Object -First 1
    if (-not $bin) { throw 'No se encontró ffmpeg.exe en el zip descargado.' }
    Copy-Item $bin.FullName $ffmpegCache -Force
  } finally { Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue }
}

# --- Python oficial "embeddable" (python.org, firmado por la Python Software Foundation) ---
# Desde la 2.3.0 EC-Cam no se compila a un .exe propio: el Control inteligente de
# aplicaciones de Windows 11 bloquea los .exe sin firma. pythonw.exe sí está firmado.
$pythonVersion = '3.12.10'
$pyZip = Join-Path $scriptDir "python-$pythonVersion-embed-amd64.zip"
if (-not (Test-Path $pyZip)) {
  Write-Host "Descargando Python $pythonVersion (embeddable)..."
  Invoke-WebRequest -Uri "https://www.python.org/ftp/python/$pythonVersion/python-$pythonVersion-embed-amd64.zip" -OutFile $pyZip
}
Expand-Archive -Path $pyZip -DestinationPath $pyDir -Force
$pth = Get-ChildItem -Path $pyDir -Filter 'python*._pth' | Select-Object -First 1
if (-not $pth) { throw 'No se encontró el archivo ._pth del Python embeddable.' }
# Que Python encuentre el código de EC-Cam (..\app).
Add-Content -Path $pth.FullName -Value '..\app' -Encoding ascii
foreach ($exe in 'python.exe', 'pythonw.exe') {
  $sig = Get-AuthenticodeSignature (Join-Path $pyDir $exe)
  if ($sig.Status -ne 'Valid') { throw "$exe no tiene una firma válida ($($sig.Status))." }
  Write-Host "$exe firmado por: $($sig.SignerCertificate.Subject)"
}

# --- Fecha de publicación (hora de Ciudad de México) ---
try { $tz = [TimeZoneInfo]::FindSystemTimeZoneById('Central Standard Time (Mexico)') } catch { $tz = [TimeZoneInfo]::Local }
$buildDate = [TimeZoneInfo]::ConvertTimeFromUtc([DateTime]::UtcNow, $tz).ToString('yyyy-MM-dd HH:mm')
Set-Content -Path (Join-Path $srcRoot 'eccam_build.py') -Value "BUILD_DATE = `"$buildDate`"" -Encoding ascii
Write-Host "Fecha de publicación: $buildDate"

# --- Código de EC-Cam ---
Get-ChildItem -Path $srcRoot -Filter '*.py' | Copy-Item -Destination $appDir -Force
Copy-Item (Join-Path $srcRoot 'web') $appDir -Recurse -Force
Copy-Item (Join-Path $srcRoot 'certs') $appDir -Recurse -Force
Copy-Item $ffmpegCache (Join-Path $appDir 'ffmpeg.exe') -Force
Copy-Item (Join-Path $projectRoot 'LICENSE-TOPO.txt') $appRoot -Force
Copy-Item (Join-Path $projectRoot 'LICENSE') $appRoot -Force
# Precompilar (arranca más rápido) y comprobar que todo importa con el Python embebido.
Invoke-Checked (Join-Path $pyDir 'python.exe') @('-m', 'compileall', '-q', $appDir)
$check = & (Join-Path $pyDir 'python.exe') (Join-Path $appDir 'eccam_server.py') --version
if ($LASTEXITCODE -ne 0) { throw 'EC-Cam no arrancó con el Python embebido.' }
Write-Host "Verificado: $check"

# --- Instalador (Inno Setup) ---
$iscc = @("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe", "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe") |
  Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) {
  Write-Warning "No encontré Inno Setup 6. EC-Cam ya está en $appRoot (puedes copiar esa carpeta tal cual)."
  Write-Warning 'Instala Inno Setup 6 desde https://jrsoftware.org/isinfo.php y vuelve a correr este script para generar el instalador.'
  exit 0
}
Write-Host 'Generando el instalador...'
Invoke-Checked $iscc @("/DAppVersion=$version", "/DSourceDir=$appRoot", "/O$outDir", (Join-Path $scriptDir 'eccam.iss'))
Write-Host "Listo: $outDir\EC-Cam-Setup-$version.exe" -ForegroundColor Green
