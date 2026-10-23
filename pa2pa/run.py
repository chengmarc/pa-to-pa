"""Plays a grid of games against the local model server and logs each to data/runs/<time>-<scenario>.jsonl.

    python -m pa2pa.run --scenario secondhand                       # every case x strategy x persona x tier
    python -m pa2pa.run --cases bike --strategies voss no-tactic --personas p01 p02 --seeds 2

The grid is case x strategy x persona x tier x seed. Strategies are persuader-strategies/<name>.md, personas
persuadee-personas/<name>.md.
Tiers: t1_vanilla (the persuadee gets no persona) and t2_secretary (it gets its principal's persona).
"""
import argparse
import itertools
import json
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import game, llm

ROOT = game.ROOT


def names(folder):
    return sorted(p.stem for p in (ROOT / folder).glob("*.md") if p.stem != "README")


def text(folder, name):
    return (ROOT / folder / f"{name}.md").read_text(encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scenario", default="secondhand")
    ap.add_argument("--cases", nargs="*", help="case ids (default: all)")
    ap.add_argument("--strategies", nargs="*", help="persuader-strategies/ names (default: all)")
    ap.add_argument("--personas", nargs="*", help="persuadee-personas/ names (default: all)")
    ap.add_argument("--tiers", nargs="*", default=["t1_vanilla", "t2_secretary"],
                    choices=["t1_vanilla", "t2_secretary"])
    ap.add_argument("--seeds", type=int, default=1, help="games per cell")
    ap.add_argument("--max-turns", type=int, default=20, help="messages before it ends with no deal")
    ap.add_argument("--workers", type=int, default=4, help="games at once; match serve.ps1's slots")
    ap.add_argument("--thinking", action="store_true", help="let the model think before each message (slower)")
    ap.add_argument("--guard", action="store_true", help="enforce the persuadee's floor in code too")
    args = ap.parse_args()

    if not llm.ready():
        raise SystemExit(f"No server at {llm.SERVER}; start it with scripts/serve.ps1")
    config = game.load(args.scenario)
    cases = [c for c in config["cases"] if not args.cases or c["id"] in args.cases]
    strategies = args.strategies or names("persuader-strategies")
    personas = args.personas or names("persuadee-personas")
    grid = list(itertools.product(cases, strategies, personas, args.tiers, range(args.seeds)))
    model = llm.model()

    out = ROOT / "data" / "runs" / f"{time.strftime('%Y%m%d-%H%M%S')}-{args.scenario}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    lock = threading.Lock()
    print(f"{len(grid)} games on {model} -> {out.relative_to(ROOT)}")

    def one(cell):
        case, strategy, persona, tier, seed = cell
        record = {"scenario": args.scenario, "case": case["id"], "price_H": case["price_H"], "price_L": case["price_L"],
                  "strategy": strategy, "persona": persona, "tier": tier, "seed": seed, "model": model,
                  "thinking": args.thinking, "guard": args.guard, "max_turns": args.max_turns}
        try:
            record.update(game.play(args.scenario, config, case, text("persuader-strategies", strategy),
                                    text("persuadee-personas", persona) if tier == "t2_secretary" else None,
                                    seed=seed, max_turns=args.max_turns, thinking=args.thinking, guard=args.guard))
        except Exception as e:   # one failed game shouldn't stop the run; it's logged with its error
            record["error"] = f"{type(e).__name__}: {e}"
        with lock, out.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record

    started, records = time.time(), []
    with ThreadPoolExecutor(args.workers) as ex:
        for i, future in enumerate(as_completed([ex.submit(one, cell) for cell in grid]), 1):
            r = future.result()
            o = r.get("outcome") or {}
            print(f"[{i}/{len(grid)}] {r['case']} {r['strategy']} {r['persona']} {r['tier']} s{r['seed']}: "
                  + (r["error"] if "error" in r else
                     f"price {o['price']:g} advance {o['advance']:.2f} in {o['turns']} turns" if o["deal"] else
                     f"no deal in {o['turns']} turns"), flush=True)
            records.append(r)
    print(f"\nDone in {time.time() - started:.0f} s.")
    summary(records)


def summary(records):
    """Per strategy x tier: games, deal rate, mean advance over deals, breach rate over deals."""
    cells = defaultdict(list)
    for r in records:
        cells[(r["strategy"], r["tier"])].append(r)
    print(f"\n{'strategy':<18}{'tier':<14}{'games':>6}{'deals':>7}{'advance':>9}{'breach':>8}{'errors':>8}")
    for (strategy, tier), rs in sorted(cells.items()):
        deals = [r["outcome"] for r in rs if r.get("outcome", {}).get("deal")]
        advance = sum(o["advance"] for o in deals) / len(deals) if deals else float("nan")
        breach = sum(o["breach"] for o in deals) / len(deals) if deals else float("nan")
        errors = sum("error" in r for r in rs)
        print(f"{strategy:<18}{tier:<14}{len(rs):>6}{len(deals) / len(rs):>7.0%}{advance:>9.2f}{breach:>8.0%}{errors:>8}")


if __name__ == "__main__":
    main()
