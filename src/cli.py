"""PA-to-PA, run with Python 3.11+ on Windows or macOS. Nothing to install: the app is standard library only.

    python pa-to-pa.pyw                     set up what's missing, start the model server, open the runs page
    python pa-to-pa.pyw run --strategy ... --tier ...   one run from the command line (run --help for the options)
    python pa-to-pa.pyw serve [model]       serve a local model in this window, until Ctrl+C (default qwen3.5-9b)
    python pa-to-pa.pyw fetch               download llama.cpp and the models into runtime/ (~6 GB)
"""
import argparse
import contextlib
import sys
import urllib.request
import webbrowser

from . import llm, run, runtime, ui

MODEL = "qwen3.5-9b"   # the model the launcher serves


def up(url):
    try:
        with urllib.request.urlopen(url, timeout=2):
            return True
    except OSError:
        return False


@contextlib.contextmanager
def console():
    """A console window for a while, when there's none (a double-clicked .pyw on Windows): the first-time download
    shows its progress there."""
    if sys.platform != "win32" or sys.__stdout__ is not None:
        yield
        return
    import ctypes
    ctypes.windll.kernel32.AllocConsole()
    saved = sys.stdout, sys.stderr
    sys.stdout = sys.stderr = open("CONOUT$", "w", encoding="utf-8", buffering=1)
    try:
        yield
    finally:
        sys.stdout.close()
        sys.stdout, sys.stderr = saved
        ctypes.windll.kernel32.FreeConsole()


def launch():
    """Each step is skipped when it's already done, so this is safe to run any time. The page opens straight away and
    enables the model once it has loaded."""
    page = f"http://{ui.ADDRESS[0]}:{ui.ADDRESS[1]}"
    if up(page):
        print("The runs page is already running.")
        webbrowser.open(page)
        return
    if not runtime.fetched(MODEL):
        with console():
            print("== Downloading llama.cpp and the models (~6 GB, first time only) ==")
            runtime.fetch()
    server = None
    if not llm.ready(MODEL):
        print(f"== Starting the {MODEL} server (log: appdata/logs/server-{MODEL}.log) ==")
        server = runtime.start(MODEL)
    # the page shows the model as starting until it has loaded, and Quit stops it too
    ui.main(MODEL if server else None, server)


def serve(argv):
    ap = argparse.ArgumentParser(prog="pa-to-pa.pyw serve", description="Serve a local model in this window.")
    ap.add_argument("model", nargs="?", default=MODEL, choices=list(runtime.local_models()))
    ap.add_argument("--context", type=int, help="tokens, shared by the slots (default: the model's in models.json)")
    ap.add_argument("--parallel", type=int, help="slots: games served at once (default: the model's)")
    args = ap.parse_args(argv)
    return runtime.serve(args.model, args.context, args.parallel)


def main(argv):
    command, rest = (argv[0], argv[1:]) if argv else (None, [])
    if command is None:
        launch()
    elif command == "run":
        run.main(rest)
    elif command == "serve":
        raise SystemExit(serve(rest))
    elif command == "fetch":
        runtime.fetch()
    elif command in ("-h", "--help", "help"):
        print(__doc__)
    else:
        raise SystemExit(f"Unknown command: {command}\n{__doc__}")
