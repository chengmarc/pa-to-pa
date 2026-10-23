"""runtime/: llama.cpp and the local models (the "local" blocks of models.json), and serving them. The same on Windows
(the CUDA 12.4 build) and macOS (the Metal build).

fetch() downloads what's missing; an interrupted download resumes. serve() runs a model server in this window;
start() starts one in the background that outlives this process, which is what the launcher does.
"""
import json
import platform
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

from .paths import LOGS, RUNTIME, SRC

# llama.cpp b10434, per platform: Windows, the CUDA 12.4 build and its CUDA runtime (NVIDIA driver with CUDA 12.4+);
# macOS, the Metal build. A .zip unpacks flat; a .tar.gz has one top folder, which is dropped.
RELEASE = "https://github.com/ggml-org/llama.cpp/releases/download/b10434/"
BUILDS = {
    "windows": [RELEASE + "llama-b10434-bin-win-cuda-12.4-x64.zip", RELEASE + "cudart-llama-bin-win-cuda-12.4-x64.zip"],
    "mac-arm64": [RELEASE + "llama-b10434-bin-macos-arm64.tar.gz"],
    "mac-x64": [RELEASE + "llama-b10434-bin-macos-x64.tar.gz"],
}
LLAMA = RUNTIME / "llama"
SERVER = LLAMA / ("llama-server.exe" if sys.platform == "win32" else "llama-server")
STAGING = SRC.parent / "build" / "downloads"


def system():
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "darwin":
        return "mac-arm64" if platform.machine() == "arm64" else "mac-x64"
    raise SystemExit(f"Unsupported system: {sys.platform}. This runs on Windows and macOS.")


def local_models():
    """{name: its "local" block} for the models served from runtime/."""
    models = json.loads((SRC / "models.json").read_text(encoding="utf-8"))
    return {name: m["local"] for name, m in models.items() if isinstance(m, dict) and "local" in m}


def port(name):
    return urllib.parse.urlparse(json.loads((SRC / "models.json").read_text(encoding="utf-8"))[name]["url"]).port


def gguf(name):
    return RUNTIME / "model" / local_models()[name]["file"]


def fetched(name):
    """Whether llama.cpp and this model are in runtime/."""
    return SERVER.exists() and gguf(name).exists()


def download(url, dest):
    """url to dest. An unfinished download is dest.part and resumes from where it stopped; a stalled or dropped
    connection is retried. urllib uses the system's proxy setting on Windows and macOS."""
    if dest.exists():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    print(f"Downloading {dest.name}...")
    for attempt in range(6):
        have = part.stat().st_size if part.exists() else 0
        req = urllib.request.Request(url, headers={"Range": f"bytes={have}-"} if have else {})
        try:
            with urllib.request.urlopen(req, timeout=60) as res:
                if have and res.status != 206:   # the server ignored the range: start over
                    have = 0
                total = have + int(res.headers.get("Content-Length", 0))
                with part.open("ab" if have else "wb") as f:
                    shown = -1
                    while chunk := res.read(1 << 20):
                        f.write(chunk)
                        have += len(chunk)
                        if total and (pct := have * 100 // total) != shown:
                            shown = pct
                            print(f"\r  {pct:3d}%  {have >> 20} of {total >> 20} MB", end="", flush=True)
            print()
            part.replace(dest)
            return
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if isinstance(e, urllib.error.HTTPError) and e.code == 416:   # already complete
                part.replace(dest)
                return
            print(f"\n  {e}; retrying ({attempt + 1}/5)...")
            time.sleep(5)
    raise SystemExit(f"Download of {dest.name} failed; run this again to resume it.")


def unpack(archive, into):
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as z:
            z.extractall(into)
        return
    with tarfile.open(archive) as t:
        members = []
        for m in t.getmembers():   # drop the one top folder
            parts = m.name.split("/", 1)
            if len(parts) == 2 and parts[1]:
                m.name = parts[1]
                members.append(m)
        # filter="data" (no paths outside into/, no device files) exists from Python 3.11.4
        t.extractall(into, members=members, **({"filter": "data"} if hasattr(tarfile, "data_filter") else {}))


def fetch():
    """Downloads what's missing: this platform's llama.cpp build into runtime/llama/, every local model into
    runtime/model/."""
    if not LLAMA.exists():
        print(f"== runtime/llama ({system()}) ==")
        new = LLAMA.with_name("llama.new")
        shutil.rmtree(new, ignore_errors=True)
        for url in BUILDS[system()]:
            archive = STAGING / url.rsplit("/", 1)[1]
            download(url, archive)
            unpack(archive, new)
            archive.unlink()
        new.rename(LLAMA)
    for name, m in local_models().items():
        dest = gguf(name)
        if dest.exists():
            continue
        print(f"== runtime/model/{dest.name} ==")
        download(m["download"], dest)
        if dest.stat().st_size != m["size"]:
            raise SystemExit(f"{dest} has the wrong size; delete it and run this again.")
    shutil.rmtree(STAGING.parent, ignore_errors=True)


def command(name, context=None, parallel=None):
    """llama-server's command line for a local model: the port from its url, the rest from its "local" block.
    --jinja formats messages with the chat template inside the model file."""
    m = local_models()[name]
    if not fetched(name):
        raise SystemExit(f"{name} isn't downloaded yet: run python pa-to-pa.pyw fetch")
    LOGS.mkdir(parents=True, exist_ok=True)
    return [str(SERVER), "-m", str(gguf(name)), "--alias", name, "--jinja", "--host", "127.0.0.1",
            "--port", str(port(name)), "-c", str(context or m["context"]), "--parallel", str(parallel or m["parallel"]),
            *m["placement"], "--log-file", str(LOGS / f"server-{name}.log")]


def serve(name, context=None, parallel=None):
    """A model server in this window, until Ctrl+C."""
    try:
        return subprocess.call(command(name, context, parallel))
    except KeyboardInterrupt:
        return 0


def start(name):
    """A model server in the background, with no window, that outlives this process unless stopped: its output in
    logs/server-<name>.out. Returns its process, for stopping it."""
    cmd = command(name)
    # Windows: no console window of its own; macOS: a session of its own, so closing Terminal doesn't stop it.
    detach = {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {"start_new_session": True}
    with (LOGS / f"server-{name}.out").open("ab") as out:
        return subprocess.Popen(cmd, stdout=out, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, **detach)
