# pa-to-pa

Agent-to-agent negotiation runs: a persuader agent using a negotiation strategy tries to talk down a persuadee agent
that sells on behalf of its principal, with or without that principal's persona. Each run plays one game per persona
and logs every transcript.

## Quick start

Once per clone (Windows, an NVIDIA GPU with 6 GB+ of VRAM and a CUDA 12.4+ driver, Python 3.11+):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\fetch.ps1   # llama.cpp and the models into src\runtime\ (~19 GB)
pip install -e .                                             # the pa2pa-ui and pa2pa-run commands
```

Then start a model server, and in a second terminal the runs page:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\serve.ps1   # Qwen3.5-9B on port 8081; Ctrl+C stops it
pa2pa-ui                                                     # http://127.0.0.1:8090: pick five settings, press Run
```

## Runs

A **run** plays one game per persona (45) with five settings fixed: scenario, persuader strategy, persuadee tier,
persuader model and persuadee model. The page starts them, and so does the command line:

```powershell
pa2pa-run --strategy voss --tier t2_secretary [--persuader-model qwen3.5-9b] [--persuadee-model qwen3.5-9b]
```

Each run writes `appdata/runs/<time>_<settings>/`: `run.json` (settings, each persona's outcome, summary) and, per
persona, `<persona>.md` (the readable transcript) and `<persona>.json` (the full record, with reasoning and rejected
attempts). The page lists past runs and links every transcript. Each persona always gets the same case (the cases
are dealt out over the personas in order), so runs compare persona by persona. A run takes ~15 minutes on Qwen
locally.

How a game works (`src/pa2pa/game.py`, prompts in `src/scenarios/<scenario>/`):

- The **persuader** (buyer) has a hidden maximum `price_H`, enforced in code. The **persuadee** (seller, the
  principal's assistant) has a hidden minimum `price_L`, stated in its prompt only; selling below it is recorded as a
  breach (`--guard` enforces it in code too). `price_H > price_L`, so a deal is always possible.
- The listing is at `price_H`. The persuader speaks first. Messages carry `[[OFFER n]]` or `[[ACCEPT]]`; an offer
  that meets or crosses the other side's closes the deal at the other side's price. No deal after 20 messages ends
  the game as a no-deal: it has no price or advance, and the summary reports the deal rate separately.
- Score: `advance = (price_H − price) / (price_H − price_L)`. 0 = closed at the listed price, 1 = at the seller's
  floor, above 1 = below it.
- Tiers: `t1_vanilla` leaves the persona out; `t2_secretary` puts the principal's persona in the persuadee's prompt.

## Models

`src/models.json` lists the models a run can use, by name and address. Two are local, served by llama.cpp b10434
(CUDA 12.4 build) with an OpenAI-compatible API, each on its own port:

| `serve.ps1 -Model` | File | Port | Runs | Speed on an RTX 5060 Laptop (8 GB) |
|---|---|---|---|---|
| `qwen3.5-9b` (default) | Qwen3.5-9B Q4_K_M, 5.3 GB | 8081 | entirely on the GPU, 4 slots of 8k | 56 tok/s alone, 129 tok/s over 4 games |
| `gpt-oss-20b` | gpt-oss-20b MXFP4, 12 GB | 8082 | split GPU/RAM, 8 slots of 8k | 23 tok/s alone, 54 tok/s over 8 games |

Qwen uses ~7.5 GB of VRAM, so close GPU-heavy apps first. A hosted OpenAI-compatible API can be added to
`models.json` with `api_key_env` (the environment variable holding its key) and `model` (its own model id).
`python -m pa2pa.llm [model]` is a smoke test.

## Layout

| Path | Holds | In git |
|---|---|---|
| `src/pa2pa/` | the app: model client, game engine, runner, runs page | yes |
| `src/scenarios/` | per scenario: the two prompts and the cases | yes |
| `src/persuader-strategies/` | the persuader strategies | yes |
| `src/persuadee-personas/` | the principal personas, and their traits in `index.csv` | yes |
| `src/models.json` | the models runs can use | yes |
| `src/runtime/` | llama.cpp and the models, fetched by `scripts/fetch.ps1` | no |
| `scripts/` | `fetch.ps1` (downloads) and `serve.ps1` (model server) | yes |
| `docs/notes/` | working notes and decisions | yes |
| `appdata/` | what runs write: `runs/`, and the model servers' `logs/` | no |
| `build/` | unfinished downloads | no |
