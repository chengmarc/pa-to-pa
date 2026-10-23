"""A local page for starting runs and reading their logs: pick the five settings, press Run.

    python -m pa2pa.ui               # opens http://127.0.0.1:8090

One run at a time. Runs are the same as python -m pa2pa.run's, logged to data/runs/.
"""
import json
import threading
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import run

ADDRESS = ("127.0.0.1", 8090)
PAGE = Path(__file__).with_name("ui.html")
state = {"busy": False, "error": None}   # the run in progress, if any, and why the last one failed to start or finish


def runs():
    """Every run's run.json, newest first, with its folder name."""
    found = []
    for path in sorted(run.RUNS.glob("*/run.json"), reverse=True):
        try:
            found.append({"folder": path.parent.name, **json.loads(path.read_text(encoding="utf-8"))})
        except (OSError, json.JSONDecodeError):
            pass   # being written right now; it shows on the next poll
    return found


def launch(settings):
    def work():
        try:
            run.start(settings)
        except Exception as e:
            state["error"] = f"{type(e).__name__}: {e}"
            traceback.print_exc()
        finally:
            state["busy"] = False
    state.update(busy=True, error=None)
    threading.Thread(target=work, daemon=True).start()


class Handler(BaseHTTPRequestHandler):
    def send(self, status, body, kind="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/":
            self.send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
        elif self.path == "/api/options":
            self.send(200, run.options())
        elif self.path == "/api/state":
            self.send(200, {**state, "runs": runs()})
        elif self.path.startswith("/runs/"):
            # /runs/<folder>/<file>: a log, only from inside data/runs
            parts = self.path.split("/")[2:]
            path = run.RUNS.joinpath(*parts).resolve() if len(parts) == 2 else None
            if path and path.parent.parent == run.RUNS.resolve() and path.suffix in (".md", ".json") and path.is_file():
                self.send(200, path.read_bytes(), "text/plain; charset=utf-8")
            else:
                self.send(404, {"error": "no such log"})
        else:
            self.send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/api/run":
            return self.send(404, {"error": "not found"})
        settings = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        opts = run.options()
        allowed = {"scenario": opts["scenario"], "strategy": opts["strategy"], "tier": opts["tier"],
                   "persuader_model": list(opts["model"]), "persuadee_model": list(opts["model"])}
        bad = [k for k in run.SETTINGS if settings.get(k) not in allowed[k]]
        if bad:
            return self.send(400, {"error": "choose " + ", ".join(bad)})
        if state["busy"]:
            return self.send(409, {"error": "a run is already in progress"})
        launch({k: settings[k] for k in run.SETTINGS})
        self.send(202, {"started": True})

    def log_message(self, *args):
        pass   # no line per poll


def main():
    server = ThreadingHTTPServer(ADDRESS, Handler)
    url = f"http://{ADDRESS[0]}:{ADDRESS[1]}"
    print(f"Runs page at {url} (Ctrl+C stops it)")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
