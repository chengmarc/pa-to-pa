"""Where things are. src/ is the app (the pa2pa package) and its models.json; context/ holds what the agents are given
(scenarios/, persuader-strategies/, persuadee-personas/); what runs write goes to appdata/."""
from pathlib import Path

SRC = Path(__file__).resolve().parent
CONTEXT = SRC.parent / "context"
RUNS = SRC.parent / "appdata" / "runs"
