# pa-to-pa

Agent-to-agent negotiation runs: a persuader agent using a negotiation strategy tries to talk down a persuadee agent
that sells on behalf of its principal, with or without that principal's persona. Each run plays one game per persona
and logs every transcript.

## Quick start

Needs Windows, an NVIDIA GPU with 6 GB+ of VRAM and a CUDA 12.4+ driver, and Python 3.11+.

**Double-click `pa2pa-ui.cmd`.** It does what's missing and opens the runs page at `http://127.0.0.1:8090`: the
first time it downloads llama.cpp and the models into `runtime\` (~19 GB) and installs the `pa2pa` package; every
time it starts the Qwen3.5-9B server in its own minimised window, if it isn't running, and waits for it to load.
Pick five settings and press Run. Closing the page's window stops the page; the model server keeps running.

The same steps by hand (`scripts\start.ps1` runs them):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\fetch.ps1   # llama.cpp and the models into runtime\
pip install -e .                                             # the pa2pa-ui and pa2pa-run commands
powershell -ExecutionPolicy Bypass -File scripts\serve.ps1   # Qwen3.5-9B on port 8081; Ctrl+C stops it
pa2pa-ui                                                     # the runs page, in a second terminal
```

## Runs

A **run** plays one game per persona (45) with five settings fixed: scenario, persuader strategy, persuadee tier,
persuader model and persuadee model. The page starts them, and so does the command line:

```powershell
pa2pa-run --strategy sy_voss --tier t2_secretary [--scenario d1_secondhand] [--persuader-model qwen3.5-9b] [--persuadee-model qwen3.5-9b]
```

Each run writes `appdata/runs/<time>_<settings>/`: `run.json` (settings, each persona's outcome, summary) and, per
persona, `<persona>.md` (the readable transcript) and `<persona>.json` (the full record, with reasoning and rejected
attempts). The page lists past runs and links every transcript. Each persona always gets the same case (the cases
are dealt out over the personas in order), so runs compare persona by persona. A run takes ~15 minutes on Qwen
locally.

How a game works (`src/game.py`, prompts in `context/scenarios/<scenario>/`):

- The **persuader** (buyer) has a hidden maximum `price_H`, enforced in code. The **persuadee** (seller, the
  principal's assistant) has a hidden minimum `price_L`, stated in its prompt only; selling below it is recorded as a
  breach (`--guard` enforces it in code too). `price_H > price_L`, so a deal is always possible.
- The listing is at `price_H`. The persuader speaks first. Messages carry `[[OFFER n]]` or `[[ACCEPT]]`; an offer
  that meets or crosses the other side's closes the deal at the other side's price. No deal after 20 messages ends
  the game as a no-deal: it has no price or advance, and the summary reports the deal rate separately.
- Score: `advance = (price_H − price) / (price_H − price_L)`. 0 = closed at the listed price, 1 = at the seller's
  floor, above 1 = below it.
- Persuadee strategies: `t1_vanilla` (Not Personalized) leaves the persona out; `t2_secretary` (Personalized) puts
  the principal's persona in the persuadee's prompt.

Every setting's ids and display labels are in `src/labels.json`:

| Setting | Values (id: label) |
|---|---|
| Scenario | `d1_secondhand`: Secondhand Item · `d2_salary`: Base Salary (not built yet) · `d3_total_comp`: Total Compensation (not built yet) |
| Persuader strategy | `s0_none`: None · `s1_generic`: Generic · `sx_fisher_ury`: Fisher-Ury · `sy_voss`: Voss |
| Persuadee strategy | `t1_vanilla`: Not Personalized · `t2_secretary`: Personalized |

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
| `src/` | the app, the `pa2pa` package: model client, game engine, runner, runs page; `models.json` and `labels.json` | yes |
| `context/scenarios/` | per scenario: the two prompts and the cases | yes |
| `context/persuader-strategies/` | the persuader strategies | yes |
| `context/persuadee-personas/` | the principal personas, and their traits in `index.csv` | yes |
| `runtime/` | llama.cpp and the models, fetched by `scripts/fetch.ps1` | no |
| `scripts/` | `start.ps1` (what `pa2pa-ui.cmd` runs), `fetch.ps1` (downloads), `serve.ps1` (model server) | yes |
| `pa2pa-ui.cmd` | the double-click entry point | yes |
| `docs/notes/` | working notes and decisions | yes |
| `appdata/` | what runs write: `runs/`, and the model servers' `logs/` | no |
| `build/` | unfinished downloads | no |
