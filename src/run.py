"""One run: every persona plays one game, with five settings fixed for the run: scenario, persuader strategy,
persuadee tier, persuader model and persuadee model. The runs page (python pa-to-pa.pyw) starts runs too.

    python pa-to-pa.pyw run --scenario d1_secondhand --strategy sy_voss --tier t2_secretary \
        --persuader-model qwen3.5-9b --persuadee-model qwen3.5-9b

Each run gets a folder appdata/results/<time>_<settings>/ with run.json (settings, progress, summary) and, per persona,
<persona>.md (the readable transcript) and <persona>.json (the full record, with reasoning and rejected attempts).
Each persona always gets the same case: the cases are dealt out over the personas in order (p_01 the first case, p_02
the second, ...), so runs compare persona by persona.
"""
import argparse
import csv
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import game, llm
from .paths import CONTEXT, RESULTS, SRC

SETTINGS = ["scenario", "strategy", "tier", "persuader_model", "persuadee_model"]
LABELS = {k: v for k, v in json.loads((SRC / "labels.json").read_text(encoding="utf-8")).items()
          if not k.startswith("_")}
TIERS = list(LABELS["tier"])


def label(kind, value):
    """A setting's display label from labels.json; its id if it has none (e.g. a run from before a rename)."""
    return LABELS.get(kind, {}).get(value, value)


def names(folder):
    return sorted(p.stem for p in (CONTEXT / folder).glob("*.md") if p.stem != "README")


def options():
    """Each setting's values in labels.json order, as {id, label, ready}: a scenario or strategy is ready once its
    folder or file exists in context/. Models come in models.json order, with why (the reason one isn't ready) and
    local (served from runtime/, so not ready may just mean still loading)."""
    exists = {"scenario": lambda v: (CONTEXT / "scenarios" / v / "cases.json").exists(),
              "strategy": lambda v: (CONTEXT / "persuader-strategies" / f"{v}.md").exists(),
              "tier": lambda v: True}
    found = {k: [{"id": v, "label": l, "ready": exists[k](v)} for v, l in LABELS[k].items()] for k in exists}
    models = [{"id": m, "label": llm.label(m), "why": llm.why_not(m), "local": "local" in spec}
              for m, spec in llm.models().items()]
    return {**found, "model": [{**m, "ready": m["why"] is None} for m in models]}


def traits():
    """persuadee-personas/index.csv by persona id, if there is one."""
    path = CONTEXT / "persuadee-personas" / "index.csv"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return {row.pop("id"): row for row in csv.DictReader(f)}


def start(settings, workers=4, seed=0, max_turns=20, guard=False, on_game=None):
    """Plays the run and returns its folder. on_game(record) is called as each game finishes."""
    s = settings
    if not (CONTEXT / "scenarios" / s["scenario"] / "cases.json").exists():
        raise RuntimeError(f"{label('scenario', s['scenario'])} isn't built yet: "
                           f"add context\\scenarios\\{s['scenario']}\\")
    for name in ("persuader_model", "persuadee_model"):
        if why := llm.why_not(s[name]):
            raise RuntimeError(f"{llm.label(s[name])}: {why}")
    config = game.load(s["scenario"])
    strategy = (CONTEXT / "persuader-strategies" / f"{s['strategy']}.md").read_text(encoding="utf-8")
    personas, persona_traits = names("persuadee-personas"), traits()
    model = {"persuader": s["persuader_model"], "persuadee": s["persuadee_model"]}

    folder = RESULTS / (time.strftime("%Y%m%d-%H%M%S") + "_" + "_".join(
        [s["scenario"], s["strategy"], s["tier"], s["persuader_model"], "vs", s["persuadee_model"]]))
    folder.mkdir(parents=True)
    run = {"settings": s, "seed": seed, "max_turns": max_turns, "guard": guard, "games": len(personas),
           "status": "running", "started": time.strftime("%Y-%m-%d %H:%M:%S"), "results": {}}
    lock = threading.Lock()

    def save():
        (folder / "run.json").write_text(json.dumps(run, indent=2, ensure_ascii=False), encoding="utf-8")

    def one(i, persona):
        case = config["cases"][i % len(config["cases"])]
        record = {**s, "persona": persona, "traits": persona_traits.get(persona, {}), "case": case["id"],
                  "price_H": case["price_H"], "price_L": case["price_L"], "seed": seed, "guard": guard}
        try:
            text = (CONTEXT / "persuadee-personas" / f"{persona}.md").read_text(encoding="utf-8")
            record.update(game.play(s["scenario"], config, case, strategy,
                                    text if s["tier"] == "t2_secretary" else None, model,
                                    seed=seed, max_turns=max_turns, guard=guard))
        except Exception as e:   # one failed game shouldn't stop the run; it's logged with its error
            record["error"] = f"{type(e).__name__}: {e}"
        (folder / f"{persona}.json").write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
        (folder / f"{persona}.md").write_text(transcript(record, config), encoding="utf-8")
        with lock:
            run["results"][persona] = {"case": case["id"], **(record.get("outcome") or {"error": record["error"]})}
            save()
        if on_game:
            on_game(record)

    save()
    with ThreadPoolExecutor(workers) as ex:
        for future in as_completed([ex.submit(one, i, p) for i, p in enumerate(personas)]):
            future.result()
    run["results"] = dict(sorted(run["results"].items()))
    run.update(status="done", finished=time.strftime("%Y-%m-%d %H:%M:%S"), summary=summary(run["results"]))
    save()
    return folder


def summary(results):
    """Games, deals, mean advance over deals, breaches over deals, errors."""
    outcomes = list(results.values())
    deals = [o for o in outcomes if o.get("deal")]
    return {
        "games": len(outcomes),
        "deals": len(deals),
        "deal_rate": round(len(deals) / len(outcomes), 4) if outcomes else None,
        "mean_advance": round(sum(o["advance"] for o in deals) / len(deals), 4) if deals else None,
        "breaches": sum(o["breach"] for o in deals),
        "errors": sum("error" in o for o in outcomes),
    }


def transcript(record, config):
    """The game as a readable Markdown page."""
    roles, c = config.get("roles", {}), config["currency"]
    who = {r: f"{r.capitalize()} ({roles[r]})" if r in roles else r.capitalize() for r in ("persuader", "persuadee")}
    lines = [f"# {record['persona']} · {label('scenario', record['scenario'])} ({record['case']}) · "
             f"{label('strategy', record['strategy'])} · {label('tier', record['tier'])}", "",
             f"- {who['persuader']}: {record['persuader_model']}, cap {c}{record['price_H']:g} (the listed price)",
             f"- {who['persuadee']}: {record['persuadee_model']}, floor {c}{record['price_L']:g}"]
    if "error" in record:
        lines.append(f"- **Error:** {record['error']}")
    else:
        o = record["outcome"]
        lines.append(f"- **Outcome:** deal at {c}{o['price']:g}, advance {o['advance']:.2f}"
                     + (", **below the floor**" if o["breach"] else "") + f", {o['turns']} messages"
                     if o["deal"] else f"- **Outcome:** no deal after {o['turns']} messages")
    for turn in record.get("transcript", []):
        a = turn["action"]
        action = f" · {a['kind']}" + (f" {c}{a['amount']:g}" if a["amount"] is not None else "") if a else ""
        lines += ["", f"**{turn['turn'] + 1}. {who[turn['role']]}**{action}", "", turn["text"].strip()]
    if record.get("rejected"):
        lines += ["", "## Rejected attempts", ""]
        lines += [f"- {r['turn'] + 1}. {r['role']}: {r['problem']}" for r in record["rejected"]]
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pa-to-pa.pyw run", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scenario", default="d1_secondhand", choices=list(LABELS["scenario"]))
    ap.add_argument("--strategy", required=True, choices=list(LABELS["strategy"]))
    ap.add_argument("--tier", required=True, choices=TIERS)
    ap.add_argument("--persuader-model", default="qwen3.5-9b", help="a models.json name")
    ap.add_argument("--persuadee-model", default="qwen3.5-9b", help="a models.json name")
    ap.add_argument("--workers", type=int, default=4, help="games at once; match the model server's slots")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max-turns", type=int, default=20, help="messages before it ends with no deal")
    ap.add_argument("--guard", action="store_true", help="enforce the persuadee's floor in code too")
    args = ap.parse_args(argv)
    settings = {k: getattr(args, k) for k in SETTINGS}

    def show(r):
        o = r.get("outcome") or {}
        print(f"{r['persona']} {r['case']}: " + (r["error"] if "error" in r else
              f"deal at {o['price']:g}, advance {o['advance']:.2f}" if o["deal"] else "no deal"), flush=True)

    try:
        folder = start(settings, args.workers, args.seed, args.max_turns, args.guard, on_game=show)
    except RuntimeError as e:   # a setting that isn't ready: say which, without a traceback
        raise SystemExit(str(e))
    print(f"\n{json.loads((folder / 'run.json').read_text(encoding='utf-8'))['summary']}\nLogs: {folder}")

