# ============================================================
#  EC-Cam — genera el instalador de Windows
#  Requisitos (una sola vez en la PC donde compilas):
#    - Python 3.12 (python.org, marca "Add to PATH")
#    - Inno Setup 6 (jrsoftware.org/isinfo.php)
#  Uso (desde la carpeta eccam):
#    powershell -ExecutionPolicy Bypass -File .\windows\build.ps1
#  Resultado: windows\out\EC-Cam-Setup-<versión>.exe
# ============================================================
$ErrorActionPreference = 'Stop'
$scriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = (Resolve-Path (Join-Path $scriptDir '..')).Path
$ffmpegUrl   = if ($env:ECCAM_FFMPEG_URL) { $env:ECCAM_FFMPEG_URL } else { 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' }

function Invoke-Checked([string]$FilePath, [string[]]$ArgumentList = @()) {
  & $FilePath @ArgumentList
  if ($LASTEXITCODE -ne 0) { throw "$FilePath terminó con código $LASTEXITCODE" }
}

# --- versión (de eccam_server.py) ---
$version = (Select-String -Path (Join-Path $projectRoot 'eccam_server.py') -Pattern '^APP_VERSION = "(.+)"').Matches[0].Groups[1].Value
Write-Host "EC-Cam $version" -ForegroundColor Cyan

# --- Python ---
$python = $null; $pythonArgs = @()
if (Get-Command py -ErrorAction SilentlyContinue) {
  & py -3.12 --version *> $null
  if ($LASTEXITCODE -eq 0) { $python = 'py'; $pythonArgs = @('-3.12') }
}
if (-not $python -and (Get-Command python -ErrorAction SilentlyContinue)) { $python = 'python' }
if (-not $python) { throw 'Falta Python 3.12: https://www.python.org/downloads/windows/' }

& $python @pythonArgs -c 'import PyInstaller' *> $null
if ($LASTEXITCODE -ne 0) {
  Write-Host 'Instalando PyInstaller...'
  Invoke-Checked $python ($pythonArgs + @('-m', 'pip', 'install', '--user', 'pyinstaller'))
}

$distDir = Join-Path $scriptDir 'dist'
$outDir  = Join-Path $scriptDir 'out'
$appDir  = Join-Path $distDir 'eccam-server'
New-Item -ItemType Directory -Force -Path $distDir, $outDir | Out-Null

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

# --- Fecha de publicación (hora de Ciudad de México) ---
try { $tz = [TimeZoneInfo]::FindSystemTimeZoneById('Central Standard Time (Mexico)') } catch { $tz = [TimeZoneInfo]::Local }
$buildDate = [TimeZoneInfo]::ConvertTimeFromUtc([DateTime]::UtcNow, $tz).ToString('yyyy-MM-dd HH:mm')
Set-Content -Path (Join-Path $projectRoot 'eccam_build.py') -Value "BUILD_DATE = `"$buildDate`"" -Encoding ascii
Write-Host "Fecha de publicación: $buildDate"

# --- Servidor (PyInstaller, carpeta, sin consola) ---
Write-Host 'Compilando el servidor...'
Invoke-Checked $python ($pythonArgs + @(
  '-m', 'PyInstaller', '--clean', '--noconfirm', '--onedir', '--noconsole',
  '--name', 'eccam-server',
  '--icon', (Join-Path $projectRoot 'web\img\eccam.ico'),
  '--add-data', "$(Join-Path $projectRoot 'web');web",
  '--add-data', "$(Join-Path $projectRoot 'certs');certs",
  '--exclude-module', 'tkinter',
  '--distpath', $distDir,
  '--workpath', (Join-Path $scriptDir '.build'),
  '--specpath', (Join-Path $scriptDir '.build'),
  (Join-Path $projectRoot 'eccam_server.py')
))
Copy-Item $ffmpegCache (Join-Path $appDir 'ffmpeg.exe') -Force
Copy-Item (Join-Path $projectRoot 'LICENSE-TOPO.txt') $appDir -Force

# --- Instalador (Inno Setup) ---
$iscc = @("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe", "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe") |
  Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) {
  Write-Warning "No encontré Inno Setup 6. El servidor ya está en $appDir (puedes copiar esa carpeta tal cual)."
  Write-Warning 'Instala Inno Setup 6 desde https://jrsoftware.org/isinfo.php y vuelve a correr este script para generar el instalador.'
  exit 0
}
Write-Host 'Generando el instalador...'
Invoke-Checked $iscc @("/DAppVersion=$version", "/DSourceDir=$appDir", "/O$outDir", (Join-Path $scriptDir 'eccam.iss'))
Write-Host "Listo: $outDir\EC-Cam-Setup-$version.exe" -ForegroundColor Green
