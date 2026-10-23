# pa-to-pa

Research repo for the PA-to-PA persuasion paper: does conditioning a secretary
(personal-assistant) agent on its principal's real decision profile make it
more or less exploitable by an opposing agent's persuasion?

Target: ARR January 2027 → ACL 2027.

## Current scope

Two distributive scenarios, chosen because "how much was conceded" is directly
measurable on a single price axis:

- **D1** — second-hand item sale
- **D2** — single-issue salary negotiation (BATNA = competing offer)

Integrative and gatekeeping scenarios from the original plan are deferred.
See `notes/2026-10-23-scope-two-scenarios.md`.

## Local model

gpt-oss-20b (MXFP4 GGUF) served by llama.cpp b10434 (CUDA 12.4 build), the same setup as agent-2b. The model and
runtime are not in git; on a fresh clone, download them once (~13 GB):

```powershell
powershell -ExecutionPolicy Bypass -File scriptsetch.ps1
```

Start the server (OpenAI-compatible API at `http://127.0.0.1:8081/v1`; Ctrl+C stops it):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\serve.ps1
```

`scripts/llm.py` is a standard-library client: `chat(messages, reasoning_effort="low", seed=...)`. Run it directly
for a smoke test. `reasoning_effort` (low/medium/high) is passed through gpt-oss's chat template.

Needs an NVIDIA GPU with 6 GB+ of VRAM and a driver with CUDA 12.4+; llama.cpp splits the model between GPU and RAM
to fit. On an RTX 5060 Laptop (8 GB) it generates about 23 tokens/s.

## Layout

- `persuader/` — the four persuader strategies
- `persuadee/` — the 45 principal personas
- `notes/` — working notes, decisions, write-ups
- `sources/` — references, papers, links, excerpts
- `data/` — datasets and intermediate results
- `scripts/` — model server, client, analysis and helper scripts
- `runtime/`, `model/`, `logs/` — llama.cpp, the model and server logs (not in git)
