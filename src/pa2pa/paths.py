"""Where things are. src/ holds the app and everything it reads: models.json, scenarios/, persuader-strategies/,
persuadee-personas/, and the fetched runtime/. What runs write goes to appdata/ at the repo root."""
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
RUNS = SRC.parent / "appdata" / "runs"
