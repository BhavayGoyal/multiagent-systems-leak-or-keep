"""Why is the CCE interval wide in leak model E0?  Test the redundancy explanation (plan 3.1).

Claim.  In E0 one tell already shows the friend every question, so a second tell to the same friend changes nothing for
anyone and only costs the teller c.  Candidates are therefore almost indifferent about redundant tells, and a CCE can add
them almost for free.

Two experiments (two friend groups, E0, alpha = 0.2, both rules):
  1. Vary c in {0.0005, 0.001, 0.002, 0.005, 0.01, 0.02} and solve the max / min sharing CCE programs.  c enters only the
     utilities, so the payoff table is the same for every c (only the cache key would differ; the table is reused).
  2. Decompose the max-sharing CCE at the baseline c = 0.001: for every profile in its support and every type profile,
     split the tells into first tells (the friend is told by nobody else) and redundant tells (someone else also tells
     that friend).  Compare with the pure equilibrium.

Prediction written before the run: (1) the width of the interval falls as c rises; (2) at least 90% of the extra sharing
of the max-sharing CCE over the pure equilibrium is redundant tells.  Refuted if the width does not fall with c, or if
the extra sharing is mostly first tells.  (plan.md says "shrinks roughly in proportion to c"; the direction is the
testable part, and the decrease is what the explanation implies, so that is the criterion fixed here.)

Usage:  python experiments/run_e0_mechanism.py [n_workers]     (an LP pair needs about 4 to 6 GB)
Output: results/x1/e0_mechanism.json (rows saved as they finish in results/x1/e0_mechanism/, so a run resumes)
"""
import dataclasses
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
from leakgame.utility import FRIEND, homogeneous  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "results", "x1")
CELL_DIR = os.path.join(OUT, "e0_mechanism")
CS = [0.0005, 0.001, 0.002, 0.005, 0.01, 0.02]
BASE_C = 0.001
ALPHA = 0.2
RULES = ("SEATS", "BAR")
NETWORK = "two_groups"


def s_index(game, sig):
    S_idx = np.zeros(game.T, dtype=np.int64)
    for j in game.active:
        a_j = game._decode_action(j, np.int64(sig[j]), game.profiles[:, j])
        S_idx += game.rowbits[j][a_j]
    return S_idx


def tell_split(game, S_list, sig):
    """Expected (over type profiles) number of tells, first tells and redundant tells of one pure profile."""
    S = S_list[s_index(game, sig)].astype(np.int64)                 # (T, n, n)
    n_tells = S.sum(axis=(1, 2))
    n_first = (S.sum(axis=1) > 0).sum(axis=1)                       # friends told by at least one candidate
    return float(n_tells.mean()), float(n_first.mean()), float((n_tells - n_first).mean())


def task(args):
    c, rule = args
    path = os.path.join(CELL_DIR, f"c{c}_{rule}.json")
    if os.path.exists(path):
        print(f"skip c={c} {rule} (already done)", flush=True)
        return
    t0 = time.time()
    cfg = GameConfig(network=NETWORK, env="E0")
    tab = build_table(cfg, n_days=2000, seed=0, verbose=False)
    tab_c = dataclasses.replace(tab, cfg=cfg.with_(c=c))           # same simulated days; only the cost changes
    g = AgentFormGame(tab_c, homogeneous(FRIEND(ALPHA), cfg.n), rule)
    res = enumerate_pure_bne(g)
    rates = [float(g.sharing_rate(p)[0]) for p in res.profiles]
    cc = cce_lp(g, objectives=("max_sharing", "min_sharing"))
    hi, lo = cc[0].sharing_rate, cc[1].sharing_rate
    if rates:
        assert lo - 1e-7 <= min(rates) and max(rates) <= hi + 1e-7
    row = {"c": c, "rule": rule, "cce_share_max": hi, "cce_share_min": lo, "cce_width": hi - lo,
           "n_bne": res.count, "bne_share_min": min(rates) if rates else None, "bne_share_max": max(rates) if rates else None,
           "lp_status": [cc[0].status, cc[1].status]}
    # decomposition of the extreme CCEs into first and redundant tells
    allp = g.all_profiles()
    for tag, r in (("max", cc[0]), ("min", cc[1])):
        z = r.z
        supp = np.flatnonzero(z > 1e-9)
        w = z[supp] / z[supp].sum()
        splits = np.array([tell_split(g, tab.S_list, allp[k]) for k in supp])     # (support, 3)
        tells, first, red = (w @ splits).tolist()
        row[f"{tag}_cce"] = {"support": int(len(supp)), "tells": tells, "first": first, "redundant": red}
    if res.count:
        pure = np.array([tell_split(g, tab.S_list, p) for p in res.profiles])
        row["pure"] = {"tells": pure[:, 0].tolist(), "first": pure[:, 1].tolist(), "redundant": pure[:, 2].tolist()}
        k = int(np.argmax(pure[:, 0]))                                # compare with the pure BNE that tells most
        extra = row["max_cce"]["tells"] - pure[k, 0]
        row["extra_tells"] = extra
        row["extra_redundant_share"] = (row["max_cce"]["redundant"] - pure[k, 2]) / extra if extra > 1e-9 else None
    row["seconds"] = time.time() - t0
    os.makedirs(CELL_DIR, exist_ok=True)
    with open(path, "w") as f:
        json.dump(row, f, indent=1, default=float)
    print(f"  c={c} {rule}: CCE [{lo:.3f}, {hi:.3f}] width {hi - lo:.3f}; pure {rates}; "
          f"extra tells {row.get('extra_tells')}, redundant share {row.get('extra_redundant_share')}  ({row['seconds']:.0f}s)", flush=True)


def main():
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    os.makedirs(CELL_DIR, exist_ok=True)
    t0 = time.time()
    tasks = [(c, rule) for rule in RULES for c in CS]
    with get_context("spawn").Pool(processes=workers) as pool:
        for _ in pool.imap_unordered(task, tasks):
            pass
    rows = {}
    for c, rule in tasks:
        with open(os.path.join(CELL_DIR, f"c{c}_{rule}.json")) as f:
            rows[f"{rule}/{c}"] = json.load(f)
    out = {"alpha": ALPHA, "cs": CS, "base_c": BASE_C, "rows": rows}
    for rule in RULES:
        widths = [rows[f"{rule}/{c}"]["cce_width"] for c in CS]
        out[f"{rule}_widths"] = widths
        out[f"{rule}_width_falls_with_c"] = all(b <= a + 1e-9 for a, b in zip(widths, widths[1:])) and widths[-1] < widths[0] - 1e-6
        base = rows[f"{rule}/{BASE_C}"]
        out[f"{rule}_extra_redundant_share"] = base.get("extra_redundant_share")
    b = out["BAR_extra_redundant_share"]
    out["prediction_holds"] = bool(out["BAR_width_falls_with_c"] and b is not None and b >= 0.9)
    out["seconds"] = time.time() - t0
    with open(os.path.join(OUT, "e0_mechanism.json"), "w") as f:
        json.dump(out, f, indent=1, default=float)
    for rule in RULES:
        print(f"{rule}: widths over c {[round(w, 3) for w in out[rule + '_widths']]}, falls with c: {out[rule + '_width_falls_with_c']}; "
              f"redundant share of the extra sharing at c = {BASE_C}: {out[rule + '_extra_redundant_share']}")
    print("prediction holds (cut-off):", out["prediction_holds"])


if __name__ == "__main__":
    main()
