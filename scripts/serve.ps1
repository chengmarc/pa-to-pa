# Starts llama-server with one of the models, an OpenAI-compatible API, in this window. Ctrl+C stops it.
# The log goes to appdata\logs\server-<model>.log.
#   powershell -ExecutionPolicy Bypass -File scripts\serve.ps1 [-Model qwen3.5-9b] [-Port N] [-Context N] [-Parallel N]
# Each model has its own port, the one src\models.json names, so two can run at once (VRAM permitting): qwen3.5-9b on
# 8081, gpt-oss-20b on 8082. Not 8080, which is agent-2b's.
param(
    [ValidateSet("qwen3.5-9b", "gpt-oss-20b")]
    [string]$Model = "qwen3.5-9b",
    [int]$Port = 0,       # 0: the model's port below
    [int]$Context = 0,    # tokens, shared by all slots; 0: the model's default below
    [int]$Parallel = 0    # slots: games served at once; each gets Context / Parallel; 0: the model's default below
)
$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot
# Per model: its file, port, default context and slots, and where it runs.
#  - qwen3.5-9b: every layer on the GPU (-ngl 99). llama.cpp's own fitter keeps ~1 GB spare and would leave some
#    layers in RAM, at a quarter of the speed. 32k over 4 slots (8k per game) uses ~7.5 GB of an 8 GB GPU, so close
#    GPU-heavy apps first; with less free VRAM, loading fails with an out-of-memory error.
#  - gpt-oss-20b: 12 GB, so --fit on splits it between GPU and RAM to fit the VRAM free right now.
$Models = @{
    "qwen3.5-9b"  = @{ File = "qwen3.5-9b-q4_k_m.gguf"; Port = 8081; Context = 32768; Parallel = 4; Placement = @("-ngl", "99", "--fit", "off") }
    "gpt-oss-20b" = @{ File = "gpt-oss-20b-mxfp4.gguf"; Port = 8082; Context = 65536; Parallel = 8; Placement = @("--fit", "on", "--load-mode", "mmap") }
}
$m = $Models[$Model]
if (-not $Port) { $Port = $m.Port }
if (-not $Context) { $Context = $m.Context }
if (-not $Parallel) { $Parallel = $m.Parallel }
$Server = Join-Path $Root "src\runtime\llama\llama-server.exe"
$Gguf = Join-Path $Root "src\runtime\model\$($m.File)"
$Logs = Join-Path $Root "appdata\logs"

foreach ($f in @($Server, $Gguf)) {
    if (-not (Test-Path $f)) { Write-Host "Missing $f; run scripts\fetch.ps1 first." -ForegroundColor Red; exit 1 }
}
New-Item -ItemType Directory -Force $Logs | Out-Null

# --jinja: format messages with the chat template inside the model file.
$placement = $m.Placement
& $Server -m $Gguf --alias $Model --jinja --host 127.0.0.1 --port $Port `
    -c $Context --parallel $Parallel @placement --log-file (Join-Path $Logs "server-$Model.log")
exit $LASTEXITCODE
