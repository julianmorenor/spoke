# Descarga el modelo de Whisper que usa Spoke y verifica su integridad (Windows).
#   powershell -ExecutionPolicy Bypass -File tools\instalar-modelo.ps1
$ErrorActionPreference = "Stop"

$Dir    = Join-Path $env:USERPROFILE ".local\share\whisper"
$Modelo = Join-Path $Dir "ggml-large-v3-turbo.bin"
$Url    = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin"
$Sha256 = "1fc70f774d38eb169993ac391eea357ef47c88757ef72ee5943879b7e8e2bc69"

New-Item -ItemType Directory -Force -Path $Dir | Out-Null
if (-not (Test-Path $Modelo)) {
    Write-Host "==> Descargando modelo (~1,6 GB)..."
    curl.exe -L --fail -C - -o $Modelo $Url
}

Write-Host "==> Verificando SHA-256..."
$Actual = (Get-FileHash $Modelo -Algorithm SHA256).Hash.ToLower()
if ($Actual -ne $Sha256) {
    Write-Error "El checksum no coincide (descarga corrupta). Borra $Modelo y reintenta."
}
Write-Host "Modelo listo en $Modelo"
