# pa-to-pa

Agent-to-agent negotiation runs: a persuader agent using a negotiation strategy tries to talk down a persuadee agent
that sells on behalf of its principal, with or without that principal's persona. Each run plays one game per persona
and logs every transcript.

## Quick start

Needs Python 3.11+ and nothing else installed: the app is standard library only. Windows needs an NVIDIA GPU with
6 GB+ of VRAM and a CUDA 12.4+ driver; macOS runs the models on Apple's GPU (Metal), best on Apple silicon.

On Windows, double-click `main.pyw` (`.pyw`: no console window). On macOS, or from any terminal:

```
python main.pyw          # python3 on macOS
```

It does what's missing and opens the runs page at `http://127.0.0.1:8090`: the first time, it downloads this
platform's llama.cpp and the model into `runtime/` (~6 GB, resumes if interrupted; on Windows a console window shows
the progress); every time, it starts the Qwen3.5-9B server in the background if it isn't running. The page opens
straight away, with a spinner on the model while it loads (about 10 s), then enables it. Pick five settings and press
Run.

**Quit** on the page stops the page and the model server it started. So does closing the page: about 15 s after the
tab closes, or within 3 minutes if the whole browser closes. A run in progress finishes first. Without a console,
output and errors go to `logs/pa-to-pa.log`, and an error at launch shows in a message box.

The other commands:

```
python main.pyw run --strategy sy_voss --tier t2_secretary   # a run from the command line (run --help)
python main.pyw serve [model]                                # a model server in this window, until Ctrl+C
python main.pyw fetch                                        # just the downloads
```

## Runs

A **run** plays one game per persona file in `context/persuadee-personas/`, however many there are, with five
settings fixed: scenario, persuader strategy, persuadee tier, persuader model and persuadee model. The page starts
them, and so does `python main.pyw run`, which also takes `--scenario`, `--persuader-model` and `--persuadee-model`
(default `d1_secondhand` and `qwen3.5-9b`).

Each run writes a folder in `results/`, named as the page names it, then the models, then when it started:

```
results/Secondhand Item - Voss - Personalized - Qwen3.5-9B (Local) vs Qwen3.5-9B (Local) - 2026-10-23 14.36.33/
```

It holds `run.json` (settings, each persona's outcome, summary) and, per persona, `<persona>.md` (the readable
transcript) and `<persona>.json` (the full record, with reasoning and rejected attempts). The page lists past runs,
newest first, and links every transcript. Each persona always gets the same case (the cases are dealt out over the
personas in order), so runs compare persona by persona. A run takes about 20 seconds per persona on Qwen locally.

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

`src/models.json` lists the models a run can use, by id, with their labels on the page:

| Id | Label | Status |
|---|---|---|
| `qwen3.5-9b` | Qwen3.5-9B (Local) | ready: runs on this machine |
| `claude-api` | Claude (API) | slot, not set up yet: needs an Anthropic API key and a client for Anthropic's Messages API |
| `chatgpt-api` | ChatGPT (API) | slot, not set up yet: needs an OpenAI API key and a model id |

A slot shows on the page as a disabled pill whose tooltip says what's missing. API access is billed separately from the
Claude Max and ChatGPT/Codex subscriptions, which don't include API keys.

The local one is `qwen3.5-9b`, Qwen3.5-9B Q4_K_M
(5.3 GB), served by llama.cpp b10434 (the CUDA 12.4 build on Windows, the Metal build on macOS) with an
OpenAI-compatible API on port 8081, entirely on the GPU with 4 slots of 8k tokens. Its file, download link and server
settings are in its `local` block there. On an RTX 5060 Laptop (8 GB) it generates 56 tok/s alone and 129 tok/s over
4 games; it uses ~7.5 GB of VRAM, so close GPU-heavy apps first.

Another hosted OpenAI-compatible API can be added to `models.json` with `api_key_env` (the environment variable holding
its key) and `model` (its own model id).

## Layout

| Path | Holds | In git |
|---|---|---|
| `main.pyw` | the entry point: loads `src/` as the `pa2pa` package and runs a command | yes |
| `src/` | the app, the `pa2pa` package: commands, runtime (downloads, model servers), model client, game engine, runner, runs page; `models.json` and `labels.json` | yes |
| `context/scenarios/` | per scenario: the two prompts and the cases | yes |
| `context/persuader-strategies/` | the persuader strategies | yes |
| `context/persuadee-personas/` | the principal personas, and their traits in `index.csv` | yes |
| `runtime/` | llama.cpp and the models, fetched by `python main.pyw fetch` | no |
| `docs/notes/` | working notes and decisions | yes |
| `results/` | what runs write: a folder per run | no |
| `logs/` | the launcher's and the model servers' logs | no |
| `build/` | unfinished downloads | no |
