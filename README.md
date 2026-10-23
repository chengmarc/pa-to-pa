# pa-to-pa

Agent-to-agent negotiation runs: a persuader agent using a negotiation strategy tries to talk down a persuadee agent
that sells on behalf of its principal, with or without that principal's persona. Each run plays one game per persona
and logs every transcript.

## Quick start

Needs Python 3.11+ and nothing else installed: the app is standard library only. Windows needs an NVIDIA GPU with
6 GB+ of VRAM and a CUDA 12.4+ driver; macOS runs the models on Apple's GPU (Metal), best on Apple silicon.

```
python pa-to-pa.py          # python3 on macOS; on Windows, double-clicking pa-to-pa.py does the same
```

It does what's missing and opens the runs page at `http://127.0.0.1:8090`: the first time, it downloads this
platform's llama.cpp and the models into `runtime/` (~19 GB, resumes if interrupted); every time, it starts the
Qwen3.5-9B server in the background if it isn't running (on Windows, in its own minimised window) and waits for it to
load. Pick five settings and press Run. Ctrl+C or closing the window stops the page; the model server keeps running.

The other commands:

```
python pa-to-pa.py run --strategy sy_voss --tier t2_secretary   # a run from the command line (run --help)
python pa-to-pa.py serve [model]                                # a model server in this window, until Ctrl+C
python pa-to-pa.py fetch                                        # just the downloads
```

## Runs

A **run** plays one game per persona (45) with five settings fixed: scenario, persuader strategy, persuadee tier,
persuader model and persuadee model. The page starts them, and so does `python pa-to-pa.py run`, which also takes
`--scenario`, `--persuader-model` and `--persuadee-model` (default `d1_secondhand` and `qwen3.5-9b`).

Each run writes `appdata/results/<time>_<settings>/`: `run.json` (settings, each persona's outcome, summary) and, per
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

`src/models.json` lists the models a run can use, by name and address. Two are local, served by llama.cpp b10434 (the
CUDA 12.4 build on Windows, the Metal build on macOS) with an OpenAI-compatible API, each on its own port. Their
files, download links and server settings are in their `local` blocks there:

| `serve` model | File | Port | Runs | Speed on an RTX 5060 Laptop (8 GB) |
|---|---|---|---|---|
| `qwen3.5-9b` (default) | Qwen3.5-9B Q4_K_M, 5.3 GB | 8081 | entirely on the GPU, 4 slots of 8k | 56 tok/s alone, 129 tok/s over 4 games |
| `gpt-oss-20b` | gpt-oss-20b MXFP4, 12 GB | 8082 | split GPU/RAM, 8 slots of 8k | 23 tok/s alone, 54 tok/s over 8 games |

Qwen uses ~7.5 GB of VRAM, so close GPU-heavy apps first. A hosted OpenAI-compatible API can be added to
`models.json` with `api_key_env` (the environment variable holding its key) and `model` (its own model id).

## Layout

| Path | Holds | In git |
|---|---|---|
| `pa-to-pa.py` | the entry point: loads `src/` as the `pa2pa` package and runs a command | yes |
| `src/` | the app, the `pa2pa` package: commands, runtime (downloads, model servers), model client, game engine, runner, runs page; `models.json` and `labels.json` | yes |
| `context/scenarios/` | per scenario: the two prompts and the cases | yes |
| `context/persuader-strategies/` | the persuader strategies | yes |
| `context/persuadee-personas/` | the principal personas, and their traits in `index.csv` | yes |
| `runtime/` | llama.cpp and the models, fetched by `python pa-to-pa.py fetch` | no |
| `docs/notes/` | working notes and decisions | yes |
| `appdata/` | what runs write: `results/`, and the model servers' `logs/` | no |
| `build/` | unfinished downloads | no |
