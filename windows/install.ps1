# Instala Spoke en Windows: entorno virtual, dependencias, modelo y accesos directos.
#
#   powershell -ExecutionPolicy Bypass -File windows\install.ps1
#   powershell -ExecutionPolicy Bypass -File windows\install.ps1 -Autostart   # también al iniciar sesión
#   ... -SkipModel        no descarga el modelo (si ya lo tenés)
param(
    [switch]$Autostart,
    [switch]$SkipModel
)
$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $Here
Set-Location $Here

function Step($m) { Write-Host "==> $m" -ForegroundColor Cyan }

# 1. Python (3.10 - 3.13)
Step "Buscando Python 3.10-3.13"
$py = $null
foreach ($v in "3.12", "3.11", "3.13", "3.10") {
    & py "-$v" --version 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { $py = @("py", "-$v"); break }
}
if (-not $py) {
    Write-Host "No encontré Python. Instalando Python 3.12 con winget..."
    winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
    Write-Host "Cerrá y volvé a abrir PowerShell, y ejecutá este script de nuevo." -ForegroundColor Yellow
    exit 1
}

# 2. Entorno virtual + dependencias
Step "Creando entorno virtual (.venv)"
if (-not (Test-Path ".venv\Scripts\python.exe")) { & $py[0] $py[1..($py.Length-1)] -m venv .venv }
$Python  = Join-Path $Here ".venv\Scripts\python.exe"
$Pythonw = Join-Path $Here ".venv\Scripts\pythonw.exe"
Step "Instalando dependencias"
& $Python -m pip install --upgrade pip
& $Python -m pip install -r requirements.txt

# 3. ffmpeg (sólo para --test y --transcribe; el dictado en vivo no lo necesita)
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Step "Instalando ffmpeg (para transcribir archivos)"
    try { winget install -e --id Gyan.FFmpeg --accept-package-agreements --accept-source-agreements }
    catch { Write-Host "No se pudo instalar ffmpeg; el dictado en vivo funciona igual." -ForegroundColor Yellow }
}

# 4. Modelo
if (-not $SkipModel) {
    Step "Descargando el modelo Whisper large-v3-turbo (~1,6 GB)"
    & powershell -ExecutionPolicy Bypass -File (Join-Path $Root "tools\instalar-modelo.ps1")
}

# 5. Accesos directos (Menú Inicio y, opcional, inicio de sesión)
function New-Shortcut($Path) {
    $sh = New-Object -ComObject WScript.Shell
    $lnk = $sh.CreateShortcut($Path)
    $lnk.TargetPath = $Pythonw
    $lnk.Arguments = "-m spoke"
    $lnk.WorkingDirectory = $Here
    $lnk.Description = "Spoke - dictado por voz local"
    $lnk.Save()
}
Step "Creando acceso directo en el Menú Inicio"
$start = Join-Path ([Environment]::GetFolderPath("Programs")) "Spoke.lnk"
New-Shortcut $start
if ($Autostart) {
    Step "Activando inicio automático"
    New-Shortcut (Join-Path ([Environment]::GetFolderPath("Startup")) "Spoke.lnk")
}

# 6. Verificación
Step "Verificando instalación"
& $Python -m spoke --check
Write-Host ""
Write-Host "Listo. Abrí 'Spoke' desde el Menú Inicio (o windows\spoke.bat)." -ForegroundColor Green
Write-Host "Atajo: Alt + Espacio. Logs: $env:LOCALAPPDATA\Spoke\spoke.log"
