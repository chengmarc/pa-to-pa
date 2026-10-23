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

Two local models, served by llama.cpp b10434 (CUDA 12.4 build), each with an OpenAI-compatible API on its own port:

| `-Model` | File | Port | Runs | Speed on an RTX 5060 Laptop (8 GB) |
|---|---|---|---|---|
| `qwen3.5-9b` (default) | Qwen3.5-9B Q4_K_M, 5.3 GB | 8081 | entirely on the GPU, 4 slots of 8k | 56 tok/s alone, 129 tok/s over 4 games |
| `gpt-oss-20b` | gpt-oss-20b MXFP4, 12 GB | 8082 | split GPU/RAM, 8 slots of 8k | 23 tok/s alone, 54 tok/s over 8 games |

Models and runtime are not in git; on a fresh clone, download them once (~19 GB):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\fetch.ps1
```

Start a server (Ctrl+C stops it). Qwen uses ~7.5 GB of VRAM, so close GPU-heavy apps first:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\serve.ps1 [-Model gpt-oss-20b]
```

`models.json` lists the models a run can use, by name and address. A hosted OpenAI-compatible API can be added there
with `api_key_env` (the environment variable holding its key) and `model` (its own model id). `pa2pa/llm.py` is the
client; `python -m pa2pa.llm [model]` is a smoke test.

## Running

A **run** plays one game per persona (45) with five settings fixed: scenario, persuader strategy, persuadee tier,
persuader model and persuadee model. Start the model server(s), then either open the runs page:

```powershell
python -m pa2pa.ui        # http://127.0.0.1:8090: pick the five settings, press Run
```

or run from the command line:

```powershell
python -m pa2pa.run --strategy voss --tier t2_secretary [--persuader-model qwen3.5-9b] [--persuadee-model qwen3.5-9b]
```

Each run writes a folder `data/runs/<time>_<settings>/`: `run.json` (settings, each persona's outcome, summary) and,
per persona, `<persona>.md` (the readable transcript) and `<persona>.json` (the full record, with reasoning and
rejected attempts). The page lists past runs and links every transcript. Each persona always gets the same case
(the cases are dealt out over the personas in order), so runs compare persona by persona. A run of 45 games takes
~15 minutes on Qwen locally.

How a game works (`pa2pa/game.py`, prompts in `scenarios/<scenario>/`):

- The **persuader** (buyer) has a hidden maximum `price_H`, enforced in code. The **persuadee** (seller, the
  principal's assistant) has a hidden minimum `price_L`, stated in its prompt only; selling below it is recorded as a
  breach (`--guard` enforces it in code too). `price_H > price_L`, so a deal is always possible.
- The listing is at `price_H`. The persuader speaks first. Messages carry `[[OFFER n]]` or `[[ACCEPT]]`; an offer
  that meets or crosses the other side's closes the deal at the other side's price. No deal after 20 messages ends
  the game as a no-deal: it has no price or advance, and the summary reports the deal rate separately.
- Score: `advance = (price_H − price) / (price_H − price_L)`. 0 = closed at the listed price, 1 = at the seller's
  floor, above 1 = below it.
- Tiers: `t1_vanilla` leaves the persona out; `t2_secretary` puts the principal's persona in the persuadee's prompt.

## Layout

- `persuader-strategies/` — the four persuader strategies
- `persuadee-personas/` — the 45 principal personas
- `notes/` — working notes, decisions, write-ups
- `sources/` — references, papers, links, excerpts
- `data/` — datasets and results (`data/runs/`: game logs, not in git)
- `pa2pa/` — model client, game engine, runner and runs page
- `scenarios/` — per scenario: the two prompts and the cases
- `scripts/` — model download and server
- `models.json` — the models runs can use
- `runtime/`, `model/`, `logs/` — llama.cpp, the model and server logs (not in git)
