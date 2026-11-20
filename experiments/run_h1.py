"""H1 check that does not use the own loss ell: how often does each type hold the last seat when nobody shares?

H1 says alpha* is highest for the types most likely to be pivotal.  The report measured "pivotal" with the own
loss ell, but alpha* = (ell + c)/G, so with G roughly constant the ordering of alpha* follows ell by construction.
Here pivotality is measured on fresh simulated days with no sharing at all (leakgame.analysis.pivotality_by_type).

Phase 1 (K = 2 of 6): prediction written before the run: P(rank = K | type) increases weak < average < strong, the
order of alpha* (0.10 < 0.32 < 0.38); H1 refuted if the order differs.  Outcome: holds (3.6 / 17.9 / 28.5 %).

After the merge (issue I2 of plan.md): X5 found that at K = 3 the order of alpha* is weak < strong < average.  The
merge audit then measured pivotality at K = 1, 2, 3 (1 million days each) and found the same order as alpha* at every K.
This run repeats that with 2 million days per K, so it is a confirmation, not a blind prediction; it would refute the
claim "the type most often at the margin needs the most friendliness" if the order of P(rank = K) differed from X5's
alpha* order at any K.

Output: results/h1/pivotality.json.  The top-level fields are the K = 2 baseline (unchanged since Phase 1); "by_K" has
K = 1, 2, 3 and the X5 alpha* order for comparison.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from leakgame.analysis import pivotality_by_type  # noqa: E402
from leakgame.config import GameConfig  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "results", "h1")
X5 = os.path.join(ROOT, "results", "x5")
N_DAYS = 2_000_000
X5_FILE = {1: "x5_K_1.json", 2: "x5_delta_1.json", 3: "x5_K_3.json"}      # x5_delta_1 is the K = 2 baseline


def order(values, names):
    return [names[i] for i in sorted(range(len(values)), key=lambda i: values[i])]


def main():
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    res = pivotality_by_type(GameConfig(), n_days=N_DAYS, seed=0)          # K = 2: identical to the Phase 1 output
    names = res["types"]
    for key in ("P_rank_K", "P_rank_K1", "P_hired"):
        print(f"K=2 {key:10s}", "  ".join(f"{t}: {100 * p:5.2f}% (se {100 * s:.2f})" for t, p, s in zip(names, res[key], res["se_" + key[2:]])))
    res["order_matches_alpha_star"] = order(res["P_rank_K"], names) == ["weak", "average", "strong"]

    res["by_K"] = {}
    all_match = True
    for K in (1, 2, 3):
        r = res if K == 2 else pivotality_by_type(GameConfig(K=K), n_days=N_DAYS, seed=0)
        entry = {k: r[k] for k in ("P_rank_K", "P_rank_K1", "P_hired", "se_rank_K", "se_rank_K1", "se_hired")}
        piv_order = order(r["P_rank_K"], names)
        entry["order_P_rank_K"] = piv_order
        x5_path = os.path.join(X5, X5_FILE[K])
        if os.path.exists(x5_path):
            with open(x5_path) as f:
                bt = json.load(f)["rules"]["SEATS"]["by_type"]
            a = [bt[t]["alpha_star_local"] for t in ("weak", "avg", "strong")]
            entry["x5_alpha_star"] = a
            entry["order_alpha_star"] = order(a, names)
            entry["orders_match"] = piv_order == entry["order_alpha_star"]
            all_match &= entry["orders_match"]
        res["by_K"][str(K)] = entry
        print(f"K={K}: P(holds the last seat) " + " / ".join(f"{100 * p:.1f}%" for p in r["P_rank_K"])
              + f"  order {piv_order}  | X5 alpha* order {entry.get('order_alpha_star')}  match: {entry.get('orders_match')}")
    res["orders_match_at_every_K"] = bool(all_match)
    res["seconds"] = time.time() - t0
    print("order of P(rank = K) matches the order of alpha* at every K:", res["orders_match_at_every_K"])
    with open(os.path.join(OUT, "pivotality.json"), "w") as f:
        json.dump(res, f, indent=1)


if __name__ == "__main__":
    main()
