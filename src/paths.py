"""Where things are. src/ is the app (the pa2pa package) and its models.json and labels.json; context/ holds what the
agents are given (scenarios/, persuader-strategies/, persuadee-personas/); runtime/ holds llama.cpp and the models;
what runs write goes to results/, and logs to logs/."""
from pathlib import Path

SRC = Path(__file__).resolve().parent
CONTEXT = SRC.parent / "context"
RUNTIME = SRC.parent / "runtime"
RESULTS = SRC.parent / "results"
LOGS = SRC.parent / "logs"
