# Starts llama-server with one of the models, an OpenAI-compatible API at http://127.0.0.1:8081/v1, in this window.
# Ctrl+C stops it. The log goes to logs\server.log.
#   powershell -ExecutionPolicy Bypass -File scripts\serve.ps1 [-Model qwen3.5-9b] [-Port 8081] [-Context N] [-Parallel N]
# Port 8081, not 8080, so it doesn't collide with agent-2b's server.
param(
    [ValidateSet("qwen3.5-9b", "gpt-oss-20b")]
    [string]$Model = "qwen3.5-9b",
    [int]$Port = 8081,
    [int]$Context = 0,    # tokens, shared by all slots; 0: the model's default below
    [int]$Parallel = 0    # slots: games served at once; each gets Context / Parallel; 0: the model's default below
)
$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot
# Per model: its file, the default context and slots, and where it runs.
#  - qwen3.5-9b: every layer on the GPU (-ngl 99). llama.cpp's own fitter keeps ~1 GB spare and would leave some
#    layers in RAM, at a quarter of the speed. 32k over 4 slots (8k per game) uses ~7.5 GB of an 8 GB GPU, so close
#    GPU-heavy apps first; with less free VRAM, loading fails with an out-of-memory error.
#  - gpt-oss-20b: 12 GB, so --fit on splits it between GPU and RAM to fit the VRAM free right now.
$Models = @{
    "qwen3.5-9b"  = @{ File = "qwen3.5-9b-q4_k_m.gguf"; Context = 32768; Parallel = 4; Placement = @("-ngl", "99", "--fit", "off") }
    "gpt-oss-20b" = @{ File = "gpt-oss-20b-mxfp4.gguf"; Context = 65536; Parallel = 8; Placement = @("--fit", "on", "--load-mode", "mmap") }
}
$m = $Models[$Model]
if (-not $Context) { $Context = $m.Context }
if (-not $Parallel) { $Parallel = $m.Parallel }
$Server = Join-Path $Root "runtime\llama\llama-server.exe"
$Gguf = Join-Path $Root "model\$($m.File)"
$Logs = Join-Path $Root "logs"

foreach ($f in @($Server, $Gguf)) {
    if (-not (Test-Path $f)) { Write-Host "Missing $f; run scripts\fetch.ps1 first." -ForegroundColor Red; exit 1 }
}
New-Item -ItemType Directory -Force $Logs | Out-Null

# --jinja: format messages with the chat template inside the model file.
$placement = $m.Placement
& $Server -m $Gguf --alias $Model --jinja --host 127.0.0.1 --port $Port `
    -c $Context --parallel $Parallel @placement --log-file (Join-Path $Logs "server.log")
exit $LASTEXITCODE
