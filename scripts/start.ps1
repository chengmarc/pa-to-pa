# Everything pa2pa-ui.cmd does, from a fresh clone to the runs page open in the browser. Each step is skipped when
# it's already done, so it's safe to run any time:
#   1. llama.cpp and the models into runtime\ (scripts\fetch.ps1), the first time
#   2. the pa2pa package (pip install -e), the first time
#   3. the Qwen server (scripts\serve.ps1) in its own minimised window, unless it's running; waits until it's loaded
#   4. the runs page in this window (Ctrl+C or closing the window stops it), or just the browser if it's running
$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot
$Model = "qwen3.5-9b"
$Health = "http://127.0.0.1:8081/health"   # serve.ps1's port for qwen3.5-9b
$Page = "http://127.0.0.1:8090"             # pa2pa\ui.py's address

function Test-Url([string]$Url) {
    try { return (Invoke-WebRequest $Url -UseBasicParsing -TimeoutSec 2).StatusCode -eq 200 } catch { return $false }
}

function Stop-WithMessage([string]$Message) {
    Write-Host "`n$Message" -ForegroundColor Red
    exit 1
}

if (Test-Url $Page) {
    Write-Host "The runs page is already running."
    Start-Process $Page
    exit 0
}

if (-not (Get-Command python -ErrorAction SilentlyContinue)) { Stop-WithMessage "Python 3.11+ isn't installed or isn't on PATH." }

if (-not ((Test-Path "$Root\runtime\llama\llama-server.exe") -and (Test-Path "$Root\runtime\model\*.gguf"))) {
    Write-Host "== Downloading llama.cpp and the models (~19 GB, first time only) =="
    & powershell -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot\fetch.ps1"
    if ($LASTEXITCODE -ne 0) { Stop-WithMessage "The download failed; run this again to resume it." }
}

& python -c "import pa2pa" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "== Installing the pa2pa package (first time only) =="
    & python -m pip install -e $Root
    if ($LASTEXITCODE -ne 0) { Stop-WithMessage "pip install failed." }
}

if (-not (Test-Url $Health)) {
    Write-Host "== Starting the $Model server (its own minimised window) =="
    Start-Process powershell -WindowStyle Minimized -ArgumentList @(
        "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$PSScriptRoot\serve.ps1`"", "-Model", $Model)
    $deadline = (Get-Date).AddMinutes(3)
    while (-not (Test-Url $Health)) {
        if ((Get-Date) -gt $deadline) {
            Stop-WithMessage "The model server didn't come up in 3 minutes; see appdata\logs\server-$Model.log. With too little free VRAM it fails to load: close GPU-heavy apps and try again."
        }
        Write-Host -NoNewline "."
        Start-Sleep -Seconds 2
    }
    Write-Host " loaded."
}

Write-Host "== Runs page at $Page (Ctrl+C or close this window to stop it; the model server keeps running) =="
& python -m pa2pa.ui
