# Starts llama-server with gpt-oss-20b, an OpenAI-compatible API at http://127.0.0.1:8081/v1, in this window.
# Ctrl+C stops it. The log goes to logs\server.log.
#   powershell -ExecutionPolicy Bypass -File scripts\serve.ps1 [-Port 8081] [-Context 65536] [-Parallel 1]
# Port 8081, not 8080, so it doesn't collide with agent-2b's server.
param(
    [int]$Port = 8081,
    [int]$Context = 65536,   # tokens, shared by all slots
    [int]$Parallel = 1       # slots: games served at once; each gets Context / Parallel
)
$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot
$Server = Join-Path $Root "runtime\llama\llama-server.exe"
$Model = Join-Path $Root "model\gpt-oss-20b-mxfp4.gguf"
$Logs = Join-Path $Root "logs"

foreach ($f in @($Server, $Model)) {
    if (-not (Test-Path $f)) { Write-Host "Missing $f; run scripts\fetch.ps1 first." -ForegroundColor Red; exit 1 }
}
New-Item -ItemType Directory -Force $Logs | Out-Null

# --jinja: format messages with the chat template inside the model file (gpt-oss's harmony format).
# --fit on: llama.cpp splits the model between GPU and RAM to fit the VRAM free right now.
& $Server -m $Model --alias gpt-oss-20b --jinja --host 127.0.0.1 --port $Port `
    -c $Context --parallel $Parallel --fit on --load-mode mmap --log-file (Join-Path $Logs "server.log")
exit $LASTEXITCODE
