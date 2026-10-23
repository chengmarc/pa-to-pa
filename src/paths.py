"""Where things are. src/ is the app (the pa2pa package) and its models.json and labels.json; context/ holds what the
agents are given (scenarios/, persuader-strategies/, persuadee-personas/); runtime/ holds llama.cpp and the models;
what runs and model servers write goes to appdata/."""
from pathlib import Path

SRC = Path(__file__).resolve().parent
CONTEXT = SRC.parent / "context"
RUNTIME = SRC.parent / "runtime"
RESULTS = SRC.parent / "appdata" / "results"
LOGS = SRC.parent / "appdata" / "logs"
