"""PA-to-PA's entry point: python pa-to-pa.py [run | serve | fetch] (python3 on macOS), or double-click it on Windows.
The commands are in src/cli.py. The hyphen keeps this file from being importable, so it never shadows the package."""
import importlib.util
import sys
from pathlib import Path


def load_package():
    """src/ is the pa2pa package; load it under that name, so nothing needs installing."""
    src = Path(__file__).resolve().parent / "src"
    spec = importlib.util.spec_from_file_location("pa2pa", src / "__init__.py", submodule_search_locations=[str(src)])
    sys.modules["pa2pa"] = package = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(package)


if __name__ == "__main__":
    if sys.version_info < (3, 11):
        sys.exit("PA-to-PA needs Python 3.11 or newer.")
    load_package()
    from pa2pa import cli
    try:
        cli.main(sys.argv[1:])
    except KeyboardInterrupt:
        pass
    except (Exception, SystemExit) as e:
        if isinstance(e, SystemExit) and e.code in (None, 0):
            raise
        if sys.argv[1:]:
            raise
        # double-clicked: keep the window open so the message can be read
        print(e if isinstance(e, SystemExit) else f"{type(e).__name__}: {e}")
        input("\nPress Enter to close.")
        sys.exit(1)
