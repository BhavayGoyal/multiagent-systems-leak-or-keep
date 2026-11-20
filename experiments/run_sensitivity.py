"""X5 (robustness): does the X1 staircase survive other values of the parameters that X1 held fixed?

The headline game (two friend groups, leak model E1, FRIEND(alpha) with alpha in [0, 0.5]) is re-solved
exactly while ONE parameter at a time moves away from the baseline (Delta = sigma = 1, K = 2 of n = 6):

  Delta  bonus per question seen in advance   {0.5, 1, 2}
  sigma  marking noise                         {0.5, 1, 2}
  K      seats (the cut-off tau_K moves with K) {1, 2, 3}

For every setting and hiring rule we record the break-even friendliness of each type, both from the
table formula alpha* = (ell + c) / G and as the first grid alpha at which the type tells in every pure
BNE, plus the sharing curve.  The staircase claim is checked as:
  SEATS  alpha*(weak) < alpha*(average) <= alpha*(strong)      (H1)
  BAR    ell = 0 for every type and every type tells from the first alpha > 0 on the grid
  H2     BAR shares at least as much as SEATS at every alpha.

Output: results/x5/x5_<param>_<value>.json, results/x5/x5_summary.json
"""
import json
import os
import sys
import time
from multiprocessing import get_context

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np  # noqa: E402

from leakgame.analysis import sweep_alpha  # noqa: E402
from leakgame.config import GameConfig  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "results", "x5")
ALPHAS = [round(a, 3) for a in np.arange(0.0, 0.5001, 0.025)]
SETTINGS = [("delta", 0.5), ("delta", 1.0), ("delta", 2.0),
            ("sigma", 0.5), ("sigma", 2.0),
            ("K", 1), ("K", 3)]          # (delta, 1.0) is the baseline and stands for sigma = 1 and K = 2 too
TYPES = ("weak", "avg", "strong")
N_DAYS = 2000
N_BOOT = 100


def fname(param, value):
    return os.path.join(OUT, f"x5_{param}_{value:g}.json")


def type_summary(sweep):
    """Mean over the four candidates who can tell of loss, gain and alpha*, per type."""
    out = {}
    for th in TYPES:
        cells = [c for c in sweep["cells"] if c.endswith("/" + th)]
        lg = [sweep["loss_gain"][c] for c in cells]
        grid = [sweep["alpha_star"][c]["alpha_star_all"] for c in cells]
        out[th] = {"ell": float(np.mean([x["ell"] for x in lg])),
                   "G": float(np.mean([x["G"] for x in lg])),
                   "alpha_star_local": float(np.mean([x["alpha_star_local"] for x in lg])),
                   "alpha_star_grid_min": None if None in grid else float(min(grid)),
                   "alpha_star_grid_max": None if None in grid else float(max(grid)),
                   "never_tells_on_grid": [c for c, g in zip(cells, grid) if g is None]}
    return out


def task(setting):
    param, value = setting
    path = fname(param, value)
    if os.path.exists(path):
        print(f"skip {param}={value:g} (already done)", flush=True)
        return setting
    t0 = time.time()
    cfg = GameConfig(network="two_groups", env="E1").with_(**{param: value})
    tab = build_table_quiet(cfg)
    res = {"param": param, "value": value, "config": {"delta": cfg.delta, "sigma": cfg.sigma, "K": cfg.K,
                                                       "n": cfg.n, "m": cfg.m, "Q": cfg.Q, "c": cfg.c,
                                                       "tau": cfg.tau},
           "n_days": N_DAYS, "alphas": ALPHAS, "rules": {}}
    for rule in ("SEATS", "BAR"):
        sw = sweep_alpha(tab, rule, ALPHAS, n_boot=N_BOOT, do_replicator=False)
        for r in sw["records"]:
            r.pop("profiles", None)          # bulky; first_bne / cell_tells_first are kept
        res["rules"][rule] = {"by_type": type_summary(sw), "alpha_star": sw["alpha_star"],
                              "loss_gain": sw["loss_gain"], "records": sw["records"]}
    res["seconds"] = time.time() - t0
    with open(path, "w") as f:
        json.dump(res, f, indent=1, default=float)
    print(f"done {param}={value:g} in {res['seconds']:.0f}s", flush=True)
    return setting


def build_table_quiet(cfg):
    from leakgame.tables import build_table
    return build_table(cfg, n_days=N_DAYS, seed=0, verbose=False)


def verdicts(res):
    seats, bar = res["rules"]["SEATS"]["by_type"], res["rules"]["BAR"]["by_type"]
    a = {th: seats[th]["alpha_star_local"] for th in TYPES}
    recs_s, recs_b = res["rules"]["SEATS"]["records"], res["rules"]["BAR"]["records"]
    # BAR (Prop. 2): no own loss, so the only hurdle is the message cost c; every type switches at the same
    # alpha (~ c / G) and sharing jumps once, from none to all.
    bar_grid = {bar[th]["alpha_star_grid_min"] for th in TYPES} | {bar[th]["alpha_star_grid_max"] for th in TYPES}
    share_b = [r.get("sharing_rate_mean") for r in recs_b]
    one_jump = all(s is not None and (abs(s) < 1e-9 or abs(s - 1) < 1e-9) for s in share_b) and \
        all(x <= y + 1e-9 for x, y in zip(share_b, share_b[1:]))
    h2 = [(rb.get("sharing_rate_min", np.nan) >= rs.get("sharing_rate_max", np.nan) - 1e-12)
          for rs, rb in zip(recs_s, recs_b) if rs["alpha"] > 0]
    multi = [(rule, r["alpha"], r["n_bne"]) for rule, recs in (("SEATS", recs_s), ("BAR", recs_b))
             for r in recs if r["n_bne"] != 1]
    # H1 proper: alpha* is highest for the types most likely to be pivotal, i.e. it ranks the types exactly as the
    # own loss ell does (weak < average < strong is what this looks like at K = 2 of 6)
    ell = {th: seats[th]["ell"] for th in TYPES}
    return {"seats_order_weak_lt_avg_le_strong": bool(a["weak"] < a["avg"] <= a["strong"]),
            "seats_alpha_order_follows_loss": bool(sorted(TYPES, key=a.get) == sorted(TYPES, key=ell.get)),
            "seats_loss": ell,
            "seats_alpha_star_local": a,
            "bar_loss_zero": bool(max(abs(bar[th]["ell"]) for th in TYPES) < 1e-12),
            "bar_all_types_switch_together": bool(len(bar_grid) == 1 and None not in bar_grid),
            "bar_switch_alpha": min(bar_grid) if None not in bar_grid else None,
            "bar_one_jump_none_to_all": bool(one_jump),
            "h2_bar_ge_seats": f"{sum(h2)}/{len(h2)}",
            "h2_holds": bool(all(h2)),
            "alphas_with_several_bne": multi}


def main():
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    workers = int(os.environ.get("X5_WORKERS", "4"))      # each worker holds one payoff table build (~0.5 GB)
    with get_context("spawn").Pool(processes=min(len(SETTINGS), workers)) as pool:
        for _ in pool.imap_unordered(task, SETTINGS):
            pass
    summary = {"alphas": ALPHAS, "settings": {}}
    for param, value in SETTINGS:
        with open(fname(param, value)) as f:
            res = json.load(f)
        key = f"{param}={value:g}" if (param, value) != ("delta", 1.0) else "baseline"
        summary["settings"][key] = {
            "config": res["config"],
            "verdicts": verdicts(res),
            "share_seats": [r.get("sharing_rate_mean") for r in res["rules"]["SEATS"]["records"]],
            "share_bar": [r.get("sharing_rate_mean") for r in res["rules"]["BAR"]["records"]],
            "by_type": {rule: res["rules"][rule]["by_type"] for rule in ("SEATS", "BAR")},
        }
    summary["seconds"] = time.time() - t0
    with open(os.path.join(OUT, "x5_summary.json"), "w") as f:
        json.dump(summary, f, indent=1, default=float)
    yn = lambda b: "yes" if b else "NO"   # noqa: E731
    print(f"{'setting':10s} {'tau':>6s} | SEATS alpha* weak/avg/strong | w<a<s follows-loss | BAR ell=0 together jump@  "
          f"| H2    | several BNE at")
    for key, s in summary["settings"].items():
        v = s["verdicts"]; a = v["seats_alpha_star_local"]
        print(f"{key:10s} {s['config']['tau']:6.3f} | {a['weak']:.3f} / {a['avg']:.3f} / {a['strong']:.3f}        | "
              f"{yn(v['seats_order_weak_lt_avg_le_strong']):5s} {yn(v['seats_alpha_order_follows_loss']):12s} | "
              f"{yn(v['bar_loss_zero']):5s} "
              f"{yn(v['bar_all_types_switch_together'] and v['bar_one_jump_none_to_all']):8s} {v['bar_switch_alpha']!s:5s} | "
              f"{v['h2_bar_ge_seats']:5s} | {v['alphas_with_several_bne'] or '-'}")
    print(f"X5 done in {summary['seconds']:.0f}s")


if __name__ == "__main__":
    main()
