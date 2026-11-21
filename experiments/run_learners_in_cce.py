"""Where do the learners end up inside the CCE interval?  (Plan 3.2; uses the stored X3 runs only.)

The empirical distribution of play of a learning run is a (coarse correlated) distribution over profiles; its expected
share of tells is the run's average sharing: total tells over the run / (T x number of possible tells).  It is
computed from final_counts (pulls per arm per type cell).  Compare it with the interval [min, max] of sharing over all
CCEs of the same game (two friend groups, alpha = 0.2; E1 from run_x1.py, E0 and E2 from run_cce.py) and with the
pure-equilibrium sharing.

The run average includes the early exploration.  Where the learners settle is measured by the greedy profile at the end
of the run (in every type cell the arm with the highest estimated mean), whose sharing rate is reported as well
("greedy_*"); it is available for all six learners.

The leak-aware learner ("model-based") is left out of the run averages: its final_counts include credited observations,
not only pulls.

Prediction written before the run (plan.md 3.2): in E0 under a cut-off, learners sit inside the interval toward its high
end (redundant telling).  Refuted if a learner's average sharing is outside the interval by more than 1 percentage point
(the history is only an approximate CCE, so small excursions are possible).

Output: results/x3/learners_in_cce.json
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np  # noqa: E402

from leakgame.config import GameConfig  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
X1, X3 = os.path.join(ROOT, "results", "x1"), os.path.join(ROOT, "results", "x3")
LEARNERS = ["eps-greedy", "UCB1", "Thompson", "EXP3", "model-based", "model-ucb"]
NO_RUN_AVERAGE = {"model-based"}            # final_counts include credited observations
ALPHA = 0.2
OUTSIDE_PP = 1.0


def cce_interval(env, rule):
    f = f"x1_two_groups_{env}.json" if env == "E1" else f"x1_cce_two_groups_{env}.json"
    with open(os.path.join(X1, f)) as fh:
        rows = json.load(fh)["cce"][rule]
    r = min(rows, key=lambda r: abs(r["alpha"] - ALPHA))
    assert abs(r["alpha"] - ALPHA) < 1e-9
    with open(os.path.join(X1, f"x1_two_groups_{env}.json")) as fh:
        rec = min(json.load(fh)["rules"][rule]["records"], key=lambda r: abs(r["alpha"] - ALPHA))
    return r["cce_share_min"], r["cce_share_max"], rec["sharing_rate_min"], rec["sharing_rate_max"]


def main():
    cfg = GameConfig(network="two_groups")
    n_later = [len(cfg.later_friends(i)) for i in range(cfg.n)]
    out = {"alpha": ALPHA, "learners": LEARNERS, "settings": {}}
    worst_out = 0.0
    for name in LEARNERS:
        z = np.load(os.path.join(X3, f"x3_{name}.npz"), allow_pickle=True)
        T = int(z["T"]); fc = z["final_counts"]                                 # (B, cells, arms)
        cells = [str(c) for c in z["cell_names"]]
        players = sorted({int(c.split("/")[0][1:]) - 1 for c in cells})
        has_avg = name not in NO_RUN_AVERAGE
        if has_avg:
            assert np.allclose(fc.sum(axis=(1, 2)), T * len(players)), f"{name}: counts are not pull counts"
        tells = np.array([bin(a).count("1") for a in range(fc.shape[2])], dtype=float)
        share = (fc * tells).sum(axis=(1, 2)) / (T * cfg.n_free)               # (B,)
        # greedy profile at the end: best estimated arm among the valid arms of each cell
        valid = np.array([[a < 2 ** n_later[int(c.split("/")[0][1:]) - 1] for a in range(fc.shape[2])] for c in cells])
        means = np.where(valid[None], np.nan_to_num(z["final_means"], nan=-np.inf), -np.inf)
        greedy = means.argmax(axis=2)                                           # (B, cells)
        # each cell is one type of one candidate; types are equally likely, so expected tells = mean over types
        g_share = tells[greedy].sum(axis=1) / 3.0 / cfg.n_free
        for e, env in enumerate([str(x) for x in z["envs"]]):
            for r, rule in enumerate([str(x) for x in z["rules"]]):
                m = (z["env_idx"] == e) & (z["rule_idx"] == r)
                lo, hi, plo, phi = cce_interval(env, rule)
                key = f"{env}/{rule}"
                ent = out["settings"].setdefault(key, {"cce_min": lo, "cce_max": hi, "pure_min": plo, "pure_max": phi, "learners": {}})
                rec = {"n_runs": int(m.sum())}
                for tag, vals in (("", share[m] if has_avg else None), ("greedy_", g_share[m])):
                    if vals is None:
                        continue
                    below, above = np.maximum(lo - vals, 0), np.maximum(vals - hi, 0)
                    pos = (vals - lo) / (hi - lo) if hi - lo > 1e-6 else None
                    rec.update({f"{tag}share_mean": float(vals.mean()), f"{tag}share_min": float(vals.min()), f"{tag}share_max": float(vals.max()),
                                f"{tag}n_inside": int(((below <= 1e-9) & (above <= 1e-9)).sum()),
                                f"{tag}max_outside_pp": float(100 * max(below.max(), above.max())),
                                f"{tag}position_mean": float(pos.mean()) if pos is not None else None})
                ent["learners"][name] = rec
                if has_avg:
                    worst_out = max(worst_out, rec["max_outside_pp"])
    e0 = out["settings"]["E0/BAR"]
    avg = {k: v for k, v in e0["learners"].items() if "position_mean" in v}
    out["E0_BAR_position_by_learner"] = {k: v["position_mean"] for k, v in avg.items()}
    out["E0_BAR_greedy_position_by_learner"] = {k: v["greedy_position_mean"] for k, v in e0["learners"].items()}
    out["E0_BAR_all_inside_within_1pp"] = all(v["max_outside_pp"] <= OUTSIDE_PP for v in avg.values())
    out["E0_BAR_toward_high_end"] = all(v["position_mean"] > 0.5 for v in avg.values())
    out["prediction_holds"] = out["E0_BAR_all_inside_within_1pp"] and out["E0_BAR_toward_high_end"]
    out["max_outside_pp_any_setting"] = worst_out
    for key, ent in out["settings"].items():
        print(f"{key:9s} CCE [{100 * ent['cce_min']:5.1f}, {100 * ent['cce_max']:5.1f}]  pure [{100 * ent['pure_min']:5.1f}, {100 * ent['pure_max']:5.1f}]  "
              + "  ".join(f"{k}: {100 * v.get('share_mean', float('nan')):5.1f} ({v.get('n_inside', '-')}/{v['n_runs']} in), "
                          f"settled {100 * v['greedy_share_mean']:5.1f} ({v['greedy_n_inside']} in)" for k, v in ent["learners"].items()))
    print("E0 / cut-off position in the CCE interval (0 = low end, 1 = high end):",
          {k: round(v, 2) for k, v in out["E0_BAR_position_by_learner"].items()}, " prediction holds:", out["prediction_holds"])
    print("E0 / cut-off position of the settled (greedy) profile:", {k: round(v, 2) for k, v in out["E0_BAR_greedy_position_by_learner"].items()})
    with open(os.path.join(X3, "learners_in_cce.json"), "w") as f:
        json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()
