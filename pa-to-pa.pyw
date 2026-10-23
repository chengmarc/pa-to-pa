"""PA-to-PA's entry point. Double-click it on Windows (.pyw: no console window), or run it with
python pa-to-pa.pyw [run | serve | fetch] (python3 on macOS). The commands are in src/cli.py.
The hyphen keeps this file from being importable, so it never shadows the package."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load_package():
    """src/ is the pa2pa package; load it under that name, so nothing needs installing."""
    src = ROOT / "src"
    spec = importlib.util.spec_from_file_location("pa2pa", src / "__init__.py", submodule_search_locations=[str(src)])
    sys.modules["pa2pa"] = package = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(package)


def show_error(message):
    """Without a console, an error goes in a message box (Windows), so it isn't lost."""
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, message, "PA-to-PA", 0x10)   # MB_ICONERROR


if __name__ == "__main__":
    windowless = sys.stdout is None   # started by pythonw: a double-clicked .pyw
    if sys.version_info < (3, 11):
        (show_error if windowless else sys.exit)("PA-to-PA needs Python 3.11 or newer.")
        sys.exit(1)
    if windowless:   # what would have been printed goes to a log instead
        log = ROOT / "logs" / "pa-to-pa.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        sys.stdout = sys.stderr = log.open("a", encoding="utf-8", buffering=1)
    load_package()
    from pa2pa import cli
    try:
        cli.main(sys.argv[1:])
    except KeyboardInterrupt:
        pass
    except (Exception, SystemExit) as e:
        if isinstance(e, SystemExit) and e.code in (None, 0):
            raise
        if not windowless:
            raise
        message = str(e) if isinstance(e, SystemExit) else f"{type(e).__name__}: {e}"
        print(message)
        show_error(message + "\n\nMore in logs\\pa-to-pa.log.")
        sys.exit(1)
