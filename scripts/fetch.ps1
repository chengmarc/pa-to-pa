# Downloads what git doesn't hold: llama.cpp into runtime\llama\ and the models into model\.
# Run it again any time: it only downloads what's missing, and an interrupted download resumes.
#   powershell -ExecutionPolicy Bypass -File scripts\fetch.ps1
# Adapted from agent-2b's packaging\fetch.ps1; same llama.cpp build and gpt-oss file, so results match across the two.
$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot
$Staging = Join-Path $Root "build\downloads"
$Curl = Join-Path $env:SystemRoot "System32\curl.exe"
$Tar = Join-Path $env:SystemRoot "System32\tar.exe"

# llama.cpp b10434, CUDA 12.4 build + its CUDA runtime (NVIDIA driver with CUDA 12.4+)                ~640 MB
$LlamaUrls = @(
    "https://github.com/ggml-org/llama.cpp/releases/download/b10434/llama-b10434-bin-win-cuda-12.4-x64.zip",
    "https://github.com/ggml-org/llama.cpp/releases/download/b10434/cudart-llama-bin-win-cuda-12.4-x64.zip")
# The models, each pinned to one Hugging Face revision. Same names as serve.ps1's -Model.
$Models = @(
    # Qwen3.5-9B, Q4_K_M: fits entirely in 8 GB of VRAM                                                 ~5.3 GB
    @{ File = "qwen3.5-9b-q4_k_m.gguf"; Size = 5680522464
       Url = "https://huggingface.co/unsloth/Qwen3.5-9B-GGUF/resolve/3885219b6810b007914f3a7950a8d1b469d598a5/Qwen3.5-9B-Q4_K_M.gguf" },
    # gpt-oss-20b, MXFP4: needs 16 GB of VRAM to fit; otherwise split between GPU and RAM               ~12 GB
    @{ File = "gpt-oss-20b-mxfp4.gguf"; Size = 12109566624
       Url = "https://huggingface.co/ggml-org/gpt-oss-20b-GGUF/resolve/ef9b12f2ff56c69cf32153a02784e7a3c88bf524/gpt-oss-20b-MXFP4.gguf" }
)

# curl reads HTTPS_PROXY but not the Windows proxy setting (e.g. Clash).
if (-not $env:HTTPS_PROXY) {
    $site = [Uri]"https://github.com/"
    $proxy = [Net.WebRequest]::GetSystemWebProxy().GetProxy($site)
    if ($proxy -ne $site) {
        $env:HTTPS_PROXY = $proxy.GetLeftPart("Authority")
        Write-Host "(using the Windows proxy $env:HTTPS_PROXY)"
    }
}

function Invoke-Native([string]$Exe, [string[]]$Arguments) {
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$(Split-Path -Leaf $Exe) failed ($LASTEXITCODE)" }
}

# A finished download is <file>; an unfinished one is still <file>.part, resumed next time.
function Get-Download([string]$Url, [string]$File) {
    if (Test-Path $File) { return $File }
    New-Item -ItemType Directory -Force (Split-Path $File) | Out-Null
    Write-Host "Downloading $(Split-Path -Leaf $File)..."
    # -C -: resume a partial download; a stalled connection is dropped and retried.
    Invoke-Native $Curl @("-L", "--fail", "--retry", "5", "--retry-all-errors", "-C", "-", "--speed-limit", "10000",
                          "--speed-time", "60", "--progress-bar", "-o", "$File.part", $Url)
    Move-Item "$File.part" $File
    return $File
}

try {
    $llama = Join-Path $Root "runtime\llama"
    if (-not (Test-Path $llama)) {
        Write-Host "`n== runtime\llama =="
        $files = @($LlamaUrls | ForEach-Object { Get-Download $_ (Join-Path $Staging ($_ -split "/")[-1]) })
        if (Test-Path "$llama.new") { Remove-Item -Recurse -Force "$llama.new" }
        New-Item -ItemType Directory -Force "$llama.new" | Out-Null
        foreach ($f in $files) { Invoke-Native $Tar @("-xf", $f, "-C", "$llama.new") }
        Move-Item "$llama.new" $llama
        $files | Remove-Item
        Write-Host "Ready: runtime\llama"
    }
    foreach ($m in $Models) {
        $model = Join-Path $Root "model\$($m.File)"
        if (Test-Path $model) { continue }
        Write-Host "`n== model\$($m.File) =="
        Get-Download $m.Url $model | Out-Null
        if ((Get-Item $model).Length -ne $m.Size) { throw "model\$($m.File) has the wrong size; delete it and run this again" }
        Write-Host "Ready: model\$($m.File)"
    }
    if ((Test-Path $Staging) -and -not (Get-ChildItem $Staging)) { Remove-Item -Recurse (Split-Path $Staging) }
    Write-Host "`nDone. Start the server next: powershell -ExecutionPolicy Bypass -File scripts\serve.ps1"
} catch {
    Write-Host "`n$($_.Exception.Message)`nFailed; run this again to retry (downloads resume)." -ForegroundColor Red
    exit 1
}
