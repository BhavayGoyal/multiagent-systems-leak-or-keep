"""X1 addendum: the CCE linear programs for leak models E0 and E2 (X1 ran them for E1 only).

For every (network, env in {E0, E2}, rule, alpha) we solve max / min expected sharing over all coarse
correlated equilibria and compare that interval with the range of sharing over the pure BNEs that X1
enumerated (results/x1/x1_<network>_<env>.json, which must exist).  If the CCE interval equals the pure
range, no mixed or correlated equilibrium -- and no limit of no-regret play -- shares more or less than
the pure equilibria do.  E0 is the interesting case: it is the only leak model with several pure BNEs.

The two-groups LP has 262,144 variables (the HiGHS solve peaks near 6 GB), so by default one cell runs at
a time and two groups uses the coarser alpha grid, as in X1.

This is the independent implementation of the CCE programs for E0/E2: the pipeline's canonical files are written by
run_cce.py (results/x1/x1_cce_<network>_<env>.json, resumable, with per-row consistency assertions).  The two
implementations agree on all 212 (network, leak model, rule, alpha) rows (largest difference 0.0), and make_figures.py
asserts that the macros computed from both agree.  To keep the two sets of files apart this script writes to
results/x1/independent/.  Running it is optional (about as long as run_cce.py).

Output: results/x1/independent/x1_cce_<network>_<env>.json, results/x1/independent/x1_cce_E0E2_summary.json
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
from leakgame.solvers import cce_lp  # noqa: E402
from leakgame.tables import build_table  # noqa: E402
from leakgame.utility import FRIEND, homogeneous  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
X1 = os.path.join(ROOT, "results", "x1")                   # X1 enumerations of the pure equilibria (input)
OUT = os.path.join(X1, "independent")                      # this script's own output
ALPHAS = [round(a, 3) for a in np.arange(0.0, 0.5001, 0.025)]
ALPHAS_CCE = [round(a, 3) for a in np.arange(0.0, 0.5001, 0.05)]
NETWORKS = ["two_groups", "pairs", "star"]
ENVS = ["E0", "E2"]
TOL = 1e-6


def fname(network, env):
    return os.path.join(OUT, f"x1_cce_{network}_{env}.json")


def task(args):
    network, env = args
    if os.path.exists(fname(network, env)):
        print(f"skip {network}/{env} (already done)", flush=True)
        return args
    t0 = time.time()
    with open(os.path.join(X1, f"x1_{network}_{env}.json")) as f:
        x1 = json.load(f)
    cfg = GameConfig(network=network, env=env)
    tab = build_table(cfg, n_days=2000, seed=0, verbose=False)
    grid = ALPHAS_CCE if network == "two_groups" else ALPHAS
    res = {"network": network, "env": env, "rules": {}}
    for rule in ("SEATS", "BAR"):
        pure = {r["alpha"]: r for r in x1["rules"][rule]["records"]}
        rows = []
        for al in grid:
            g = AgentFormGame(tab, homogeneous(FRIEND(al), cfg.n), rule)
            cc = cce_lp(g, objectives=("max_sharing", "min_sharing"))
            p = pure[al]
            row = {"alpha": al, "cce_share_max": cc[0].sharing_rate, "cce_share_min": cc[1].sharing_rate,
                   "support_max": cc[0].support, "support_min": cc[1].support,
                   "status": [cc[0].status, cc[1].status], "lp_seconds": cc[0].seconds + cc[1].seconds,
                   "pure_n_bne": p["n_bne"], "pure_share_min": p.get("sharing_rate_min"),
                   "pure_share_max": p.get("sharing_rate_max")}
            row["cce_width"] = row["cce_share_max"] - row["cce_share_min"]
            row["cce_equals_pure_range"] = bool(
                p["n_bne"] > 0 and abs(row["cce_share_max"] - p["sharing_rate_max"]) < TOL
                and abs(row["cce_share_min"] - p["sharing_rate_min"]) < TOL)
            rows.append(row)
            print(f"  {network}/{env}/{rule} alpha={al:.3f}: CCE [{row['cce_share_min']:.3f}, {row['cce_share_max']:.3f}]"
                  f"  pure [{p.get('sharing_rate_min')}, {p.get('sharing_rate_max')}] ({p['n_bne']} BNE)", flush=True)
        res["rules"][rule] = rows
    res["seconds"] = time.time() - t0
    with open(fname(network, env), "w") as f:
        json.dump(res, f, indent=1, default=float)
    print(f"done {network}/{env} in {res['seconds']:.0f}s", flush=True)
    return args


def main():
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    tasks = [(net, env) for net in NETWORKS for env in ENVS]
    # largest LPs first so several workers stay busy
    tasks.sort(key=lambda t: t[0] != "two_groups")
    workers = int(os.environ.get("CCE_WORKERS", "1"))     # the two-groups LP peaks near 6 GB per worker
    with get_context("spawn").Pool(processes=workers) as pool:
        for _ in pool.imap_unordered(task, tasks):
            pass
    summary = {"tol": TOL, "cells": {}}
    n_tot = n_eq = 0
    for net, env in tasks:
        with open(fname(net, env)) as f:
            r = json.load(f)
        for rule, rows in r["rules"].items():
            eq = [row["cce_equals_pure_range"] for row in rows]
            n_tot += len(eq); n_eq += sum(eq)
            summary["cells"][f"{net}/{env}/{rule}"] = {
                "n_alpha": len(eq), "n_cce_equals_pure": int(sum(eq)),
                "max_cce_width": float(max(row["cce_width"] for row in rows)),
                "differs_at": [{"alpha": row["alpha"], "cce": [row["cce_share_min"], row["cce_share_max"]],
                                "pure": [row["pure_share_min"], row["pure_share_max"]], "n_bne": row["pure_n_bne"]}
                               for row in rows if not row["cce_equals_pure_range"]]}
    summary.update({"n_games": n_tot, "n_cce_equals_pure": n_eq, "seconds": time.time() - t0})
    with open(os.path.join(OUT, "x1_cce_E0E2_summary.json"), "w") as f:
        json.dump(summary, f, indent=1, default=float)
    print(f"CCE interval equals the pure-BNE sharing range in {n_eq} of {n_tot} games")
    for k, v in summary["cells"].items():
        print(f"  {k:22s} {v['n_cce_equals_pure']:2d}/{v['n_alpha']:2d}  max width {v['max_cce_width']:.3f}")
    print(f"done in {summary['seconds']:.0f}s")


if __name__ == "__main__":
    main()
