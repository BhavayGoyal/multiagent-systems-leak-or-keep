"""CCE linear programs for the X2 games (plan 2.5): selfish, friendly, clannish, fairness-minded and mixed populations.

For each of the 44 X2 games (two friend groups, E1, both rules) solve the two linear programs over the whole CCE
polytope: maximise and minimise the expected share of tells.  If the optima coincide, every CCE (hence every mixed
equilibrium and every limit of no-regret learning) shares the same amount as the pure equilibrium.

Checks with every game, because every pure BNE is a CCE:
  * every pure equilibrium's sharing rate lies inside the [min, max] interval of the CCE programs;
  * the pure equilibria enumerated here equal the ones run_x2.py stored for the same game (count and sharing rates).

Prediction written before the run (plan.md 2.5): the CCE interval is a single point equal to the pure equilibrium in
every X2 game, except possibly the near-indifferent games marked with a dagger in Table 2 (exact equilibrium in fewer
than 95% of bootstrap replicates).  Refuted if any unmarked game has a wider interval.

Usage:  python experiments/run_cce_x2.py [n_workers]      (a two-groups LP pair needs about 4 to 6 GB)
Rows are saved one file per game in results/x2/cce/, so an interrupted run resumes; the summary is
results/x2/x2_cce.json.
"""
import json
import os
import sys
import time
from multiprocessing import get_context

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np  # noqa: E402

from leakgame.config import GameConfig  # noqa: E402
from leakgame.game import AgentFormGame  # noqa: E402
from leakgame.solvers import cce_lp, enumerate_pure_bne  # noqa: E402
from leakgame.tables import build_table  # noqa: E402
from leakgame.utility import CLAN, FAIR, FRIEND, SELF, homogeneous  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "results", "x2")
CELL_DIR = os.path.join(OUT, "cce")
TOL = 1e-7
WIDE = 1e-6                                       # an interval wider than this is "not a single point"
N = 6


def games():
    """(id, section, index into x2.json[section], rule, population), in the order of run_x2.py."""
    out = []
    i = 0
    for rule in ("SEATS", "BAR"):
        for name, pop in (("self", homogeneous(SELF, N)), ("friend", homogeneous(FRIEND(0.2), N))):
            out.append((f"baseline_{name}_{rule}", "baseline", i, rule, pop)); i += 1
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from run_x2 import BETAS, FAIR_PARAMS              # the same grids as X2
    i = 0
    for rule in ("SEATS", "BAR"):
        for beta in BETAS:
            out.append((f"clan_{beta}_{rule}", "clan", i, rule, homogeneous(CLAN(0.2, beta), N))); i += 1
    i = 0
    for rule in ("SEATS", "BAR"):
        for a, b in FAIR_PARAMS:
            out.append((f"fair_{a}_{b}_{rule}", "fair", i, rule, homogeneous(FAIR(a, b), N))); i += 1
    mixed = [
        [FRIEND(0.2) if k % 2 == 0 else SELF for k in range(N)],
        [FRIEND(0.2) if k < 2 else SELF for k in range(N)],
        [SELF if k < 2 else FRIEND(0.2) for k in range(N)],
        [FRIEND(0.2) if k % 2 == 0 else CLAN(0.2, 0.3) for k in range(N)],
        [FAIR(0.5, 0.25) if k % 2 == 0 else FRIEND(0.2) for k in range(N)],
    ]
    i = 0
    for m, pop in enumerate(mixed):
        for rule in ("SEATS", "BAR"):
            out.append((f"mixed_{m}_{rule}", "mixed", i, rule, pop)); i += 1
    return out


def task(args):
    gid, section, idx, rule, pop = args
    path = os.path.join(CELL_DIR, f"{gid}.json")
    if os.path.exists(path):
        print(f"skip {gid} (already done)", flush=True)
        return gid
    with open(os.path.join(OUT, "x2.json")) as f:
        ref = json.load(f)[section][idx]
    assert ref["rule"] == rule, (gid, ref["rule"])
    t0 = time.time()
    tab = build_table(GameConfig(network="two_groups", env="E1"), n_days=2000, seed=0, verbose=False)
    g = AgentFormGame(tab, pop, rule)
    res = enumerate_pure_bne(g)
    rates = [float(g.sharing_rate(p)[0]) for p in res.profiles]
    same = ref["n_bne"] == res.count and (res.count == 0 or (abs(ref["sharing_rate_min"] - min(rates)) < 1e-9
                                                            and abs(ref["sharing_rate_max"] - max(rates)) < 1e-9))
    assert same, f"pure equilibria differ from x2.json at {gid}: {res.count} {rates} vs {ref['n_bne']}"
    cc = cce_lp(g, objectives=("max_sharing", "min_sharing"))
    hi, lo = cc[0].sharing_rate, cc[1].sharing_rate
    if rates:
        assert lo - TOL <= min(rates) and max(rates) <= hi + TOL, f"pure BNE outside the CCE interval at {gid}"
    boot = ref.get("bootstrap") or {}
    row = {"id": gid, "section": section, "index": idx, "rule": rule, "population": ref.get("population") or ref.get("name"),
           "beta": ref.get("beta"), "a": ref.get("a"), "b": ref.get("b"), "name": ref.get("name"),
           "cce_share_max": hi, "cce_share_min": lo, "cce_width": hi - lo,
           "lp_status": [cc[0].status, cc[1].status], "lp_seconds": cc[0].seconds + cc[1].seconds,
           "n_bne": res.count, "bne_share_min": min(rates) if rates else None, "bne_share_max": max(rates) if rates else None,
           "frac_exact_bne": boot.get("frac_exact_bne"),
           "near_indifferent": (boot.get("frac_exact_bne") is not None and boot["frac_exact_bne"] < 0.95),
           "matches_x2_equilibria": True, "seconds": time.time() - t0}
    row["cce_equals_pure_range"] = bool(rates) and abs(hi - max(rates)) < WIDE and abs(lo - min(rates)) < WIDE
    os.makedirs(CELL_DIR, exist_ok=True)
    with open(path, "w") as f:
        json.dump(row, f, indent=1, default=float)
    print(f"  {gid}: CCE share [{lo:.3f}, {hi:.3f}], {res.count} pure BNE in "
          f"[{min(rates) if rates else float('nan'):.3f}, {max(rates) if rates else float('nan'):.3f}]  ({row['seconds']:.0f}s)", flush=True)
    return gid


def main():
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    os.makedirs(CELL_DIR, exist_ok=True)
    t0 = time.time()
    G = games()
    with get_context("spawn").Pool(processes=workers) as pool:
        for _ in pool.imap_unordered(task, G):
            pass
    rows = []
    for gid, *_ in G:
        with open(os.path.join(CELL_DIR, f"{gid}.json")) as f:
            rows.append(json.load(f))
    wide = [r for r in rows if r["cce_width"] > WIDE]
    summary = {"n_games": len(rows), "n_single_point": sum(r["cce_width"] <= WIDE for r in rows),
               "n_equal_pure_range": sum(r["cce_equals_pure_range"] for r in rows),
               "wide": [r["id"] for r in wide], "wide_near_indifferent": [r["id"] for r in wide if r["near_indifferent"]],
               "max_width": max(r["cce_width"] for r in rows),
               "prediction_holds": all(r["near_indifferent"] for r in wide),
               "rows": rows, "seconds": time.time() - t0}
    with open(os.path.join(OUT, "x2_cce.json"), "w") as f:
        json.dump(summary, f, indent=1, default=float)
    print(f"{summary['n_single_point']} of {summary['n_games']} games: CCE interval is a single point; "
          f"{summary['n_equal_pure_range']} equal the pure-equilibrium range; wider: {summary['wide']}; "
          f"prediction holds: {summary['prediction_holds']}  ({summary['seconds']:.0f}s)")


if __name__ == "__main__":
    main()
