"""A local page for starting runs and reading their logs: pick the five settings, press Run.

    python main.pyw                 # opens http://127.0.0.1:8090

One run at a time. Runs are the same as python main.pyw run's, logged to results/.

It has no window to close, so it stops itself, and the model server the launcher started for it: on Quit, or once no
page is open. An open page checks in every few seconds and says goodbye when it closes; with no check-in for 15 s
after a goodbye (a reload checks in again at once), or for 3 minutes at all (a closed browser may not say goodbye), it
stops. Never during a run: it stops after the run instead.
"""
import json
import threading
import time
import traceback
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import run
from .paths import RESULTS

ADDRESS = ("127.0.0.1", 8090)
PAGE = Path(__file__).with_name("ui.html")
state = {"busy": False, "error": None}   # the run in progress, if any, and why the last one failed to start or finish
page = {"server": None}   # main()'s server, for Quit
launched = {"model": None, "process": None}   # the model server the launcher started for this page, if it did
seen = {"last": time.monotonic(), "bye": None}   # when an open page last checked in, and said goodbye
IDLE, BYE_GRACE = 180, 15   # seconds without a check-in before stopping: at all, and after a goodbye


def stop():
    """Stops the model server the launcher started, then the page."""
    if launched["process"]:
        launched["process"].terminate()
    page["server"].shutdown()


def watch():
    """Stops everything once no page is open (module docstring), checking every few seconds."""
    while True:
        time.sleep(5)
        now, last, bye = time.monotonic(), seen["last"], seen["bye"]
        closed = bye is not None and last < bye and now - bye > BYE_GRACE
        if not state["busy"] and (closed or now - last > IDLE):
            print("No page open; stopping.")
            return stop()


def options():
    """run.options(), plus whether the model the launcher started is still starting: its process is alive but the
    model isn't loaded yet. If the process has exited instead, the model's reason says so."""
    opts = run.options()
    for m in opts["model"]:
        if m["id"] != launched["model"] or m["ready"]:
            continue
        code = launched["process"].poll()
        if code is None:
            m.update(starting=True, why="Starting: loading the model, usually about 10 s.")
        else:
            m["why"] = (f"The model server stopped while starting (exit code {code}); see "
                        f"logs/server-{m['id']}.log. With too little free GPU memory it can't load: close "
                        "GPU-heavy apps and launch again.")
    return opts


def runs():
    """Every run's run.json, with its folder name, newest first (by when it started: folders are named by settings)."""
    found = []
    for path in RESULTS.glob("*/run.json"):
        try:
            found.append({"folder": path.parent.name, **json.loads(path.read_text(encoding="utf-8"))})
        except (OSError, json.JSONDecodeError):
            pass   # being written right now; it shows on the next poll
    return sorted(found, key=lambda r: r.get("started", ""), reverse=True)


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
            self.send(200, options())
        elif self.path == "/api/state":   # the page's regular poll: its check-in
            seen["last"] = time.monotonic()
            self.send(200, {**state, "runs": runs()})
        elif self.path.startswith("/results/"):
            # /results/<folder>/<file>: a log, only from inside results
            parts = [urllib.parse.unquote(p) for p in self.path.split("/")[2:]]   # folder names have spaces
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
        if self.path == "/api/bye":   # a page closing (or reloading)
            seen["bye"] = time.monotonic()
            return self.send(200, {})
        if self.path != "/api/run":
            return self.send(404, {"error": "not found"})
        settings = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        opts = options()
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
        threading.Thread(target=stop).start()

    def log_message(self, *args):
        pass   # no line per poll


def main(model=None, process=None):
    """Serves the page until Quit, no page is open, or Ctrl+C. model and process: the model server the launcher
    started for the page, shown as starting until it has loaded, and stopped with the page."""
    server = ThreadingHTTPServer(ADDRESS, Handler)
    page["server"] = server
    launched.update(model=model, process=process)
    url = f"http://{ADDRESS[0]}:{ADDRESS[1]}"
    print(f"Runs page at {url} (Quit on the page, closing it, or Ctrl+C stops it)")
    seen["last"] = time.monotonic()
    threading.Thread(target=watch, daemon=True).start()
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

