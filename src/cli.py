"""PA-to-PA, run with Python 3.11+ on Windows or macOS. Nothing to install: the app is standard library only.

    python pa-to-pa.py                         set up what's missing, start the model server, open the runs page
    python pa-to-pa.py run --strategy ... --tier ...   one run from the command line (run --help for the options)
    python pa-to-pa.py serve [model]           serve a local model in this window, until Ctrl+C (default qwen3.5-9b)
    python pa-to-pa.py fetch                   download llama.cpp and the models into runtime/ (~19 GB)
"""
import argparse
import time
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


def launch():
    """Each step is skipped when it's already done, so this is safe to run any time."""
    page = f"http://{ui.ADDRESS[0]}:{ui.ADDRESS[1]}"
    if up(page):
        print("The runs page is already running.")
        webbrowser.open(page)
        return
    if not runtime.fetched(MODEL):
        print("== Downloading llama.cpp and the models (~19 GB, first time only) ==")
        runtime.fetch()
    if not llm.ready(MODEL):
        print(f"== Starting the {MODEL} server; it keeps running after the page stops ==")
        runtime.start(MODEL)
        deadline = time.monotonic() + 180
        while not llm.ready(MODEL):
            if time.monotonic() > deadline:
                raise SystemExit(f"The model server didn't come up in 3 minutes; see appdata/logs/server-{MODEL}.log. "
                                 "With too little free GPU memory it fails to load: close GPU-heavy apps and retry.")
            print(".", end="", flush=True)
            time.sleep(2)
        print(" loaded.")
    ui.main()


def serve(argv):
    ap = argparse.ArgumentParser(prog="pa-to-pa.py serve", description="Serve a local model in this window.")
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
