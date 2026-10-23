"""A local page for starting runs and reading their logs: pick the five settings, press Run.

    python pa-to-pa.pyw                 # opens http://127.0.0.1:8090

One run at a time. Runs are the same as python pa-to-pa.pyw run's, logged to appdata/results/. Quit on the page stops
it, and the model server the launcher started for it; with no window to close, that's how it stops.
"""
import json
import threading
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import run
from .paths import RESULTS

ADDRESS = ("127.0.0.1", 8090)
PAGE = Path(__file__).with_name("ui.html")
state = {"busy": False, "error": None}   # the run in progress, if any, and why the last one failed to start or finish
quitting = {"server": None, "on_quit": None}   # main()'s server, and what to stop with it


def runs():
    """Every run's run.json, newest first, with its folder name."""
    found = []
    for path in sorted(RESULTS.glob("*/run.json"), reverse=True):
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
        elif self.path.startswith("/results/"):
            # /results/<folder>/<file>: a log, only from inside appdata/results
            parts = self.path.split("/")[2:]
            path = RESULTS.joinpath(*parts).resolve() if len(parts) == 2 else None
            if path and path.parent.parent == RESULTS.resolve() and path.suffix in (".md", ".json") and path.is_file():
                self.send(200, path.read_bytes(), "text/plain; charset=utf-8")
            else:
                self.send(404, {"error": "no such log"})
        else:
            self.send(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/api/quit":
            return self.quit()
        if self.path != "/api/run":
            return self.send(404, {"error": "not found"})
        settings = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        opts = run.options()
        ready = {k: [o["id"] for o in values if o["ready"]] for k, values in opts.items()}
        allowed = {**ready, "persuader_model": ready["model"], "persuadee_model": ready["model"]}
        bad = [k for k in run.SETTINGS if settings.get(k) not in allowed[k]]
        if bad:
            return self.send(400, {"error": "choose " + ", ".join(bad)})
        if state["busy"]:
            return self.send(409, {"error": "a run is already in progress"})
        launch({k: settings[k] for k in run.SETTINGS})
        self.send(202, {"started": True})

    def quit(self):
        if state["busy"]:
            return self.send(409, {"error": "a run is in progress; quit when it's done"})
        self.send(200, {"stopped": True})

        def stop():
            if quitting["on_quit"]:
                quitting["on_quit"]()
            quitting["server"].shutdown()
        threading.Thread(target=stop).start()

    def log_message(self, *args):
        pass   # no line per poll


def main(on_quit=None):
    """Serves the page until Quit (which also calls on_quit) or Ctrl+C."""
    server = ThreadingHTTPServer(ADDRESS, Handler)
    quitting.update(server=server, on_quit=on_quit)
    url = f"http://{ADDRESS[0]}:{ADDRESS[1]}"
    print(f"Runs page at {url} (Quit on the page, or Ctrl+C, stops it)")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

