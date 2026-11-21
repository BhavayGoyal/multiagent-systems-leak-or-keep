"""Robustness of the company-loss result (X4): other friendliness levels (plan 2.2) and other company values (plan 2.3).

2.2  X4 is solved at alpha = 0.2, where under fixed seats only the weak types tell.  Here the equilibrium is re-solved for
     alpha in {0, 0.1, ..., 0.5} at every bank size Q, on the same payoff tables as X4 (utilities are linear in alpha, so
     only the equilibrium search repeats).  Every pure BNE is evaluated, not only the first one.
     Prediction written before the run: the cut-off loses more than fixed seats at every alpha > 0, and the ratio falls
     from about 10x toward the everyone-tells ratio (2.5-4.4x) as alpha passes the strong types' threshold (about 0.38).
     Refuted if fixed seats ever lose more at some alpha > 0 and Q.

2.3  The company value V = sum_{j hired} (s_j - tau) charges tau per hire.  With a per-hire charge kappa instead,
     V_kappa = V_tau + (tau - kappa) * (number hired), and E[number hired] = sum_j P(x_j) is in the tables, so no new
     simulation is needed.  Without leaks both rules hire K = 2 on average (tau is set that way), so kappa only matters
     through the extra hires that leaks cause under a cut-off.  For every Q (alpha = 0.2) we report the value of both
     rules at kappa in {0, tau/2, tau} and the kappa at which the ranking of the rules flips.
     Prediction written before the run (plan.md 2.3): with kappa = 0 fixed seats look better at every Q.  Refuted if the
     cut-off is better at some Q with kappa = 0.

Output: results/x4/x4_robust.json
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np  # noqa: E402

from leakgame.config import GameConfig  # noqa: E402
from leakgame.game import AgentFormGame  # noqa: E402
from leakgame.solvers import enumerate_pure_bne  # noqa: E402
from leakgame.tables import build_table  # noqa: E402
from leakgame.utility import FRIEND, homogeneous  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "results", "x4")
QS = [4, 6, 9, 12, 15, 20, 25, 30, 40, 50, 64]          # as in run_x4.py (same cached tables)
ALPHAS = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]
N_BOOT = 200
RULES = ("SEATS", "BAR")


def s_index(game: AgentFormGame, sig: np.ndarray) -> np.ndarray:
    """For one pure profile: the index of the sharing matrix played at every type profile."""
    S_idx = np.zeros(game.T, dtype=np.int64)
    for j in game.active:
        a_j = game._decode_action(j, np.int64(sig[j]), game.profiles[:, j])
        S_idx += game.rowbits[j][a_j]
    return S_idx


def main():
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    rng = np.random.default_rng(0)
    rows = []
    for Q in QS:
        cfg = GameConfig(network="two_groups", env="E2", Q=Q)
        tab = build_table(cfg, n_days=2000, seed=0, verbose=False)
        T = tab.V.shape[0]
        ar = np.arange(T)
        nblk = tab.V_blocks.shape[-1]
        picks = rng.integers(0, nblk, size=(N_BOOT, nblk))                  # one set of resampled blocks for both rules
        V = tab.V.astype(float)                                              # (T, M, 2)
        Nh = tab.Px.astype(float).sum(axis=-1)                               # (T, M, 2): expected number hired
        rec = {"Q": Q, "tau": cfg.tau, "noleak": {r: {"V": float(V[:, 0, ri].mean()), "n_hired": float(Nh[:, 0, ri].mean())}
                                                  for ri, r in enumerate(RULES)},
               "allshare": {r: {"Lambda_rel": float((V[:, 0, ri].mean() - V[:, -1, ri].mean()) / V[:, 0, ri].mean())}
                            for ri, r in enumerate(RULES)},
               "alphas": {}}
        for al in ALPHAS:
            ent = {}
            vb_eq = {}
            for ri, rule in enumerate(RULES):
                g = AgentFormGame(tab, homogeneous(FRIEND(al), cfg.n), rule)
                res = enumerate_pure_bne(g)
                v0 = V[:, 0, ri].mean()
                per_bne = []
                for sig in res.profiles:
                    S_idx = s_index(g, sig)
                    per_bne.append({"sharing_rate": float(g.sharing_rate(sig)[0]), "V": float(V[ar, S_idx, ri].mean()),
                                    "n_hired": float(Nh[ar, S_idx, ri].mean()), "S_idx": S_idx})
                lam = [(v0 - b["V"]) / v0 for b in per_bne]
                first = per_bne[0] if per_bne else None
                if first is not None:                                        # bootstrap of the first BNE (as in run_x4.py)
                    blk0 = tab.V_blocks[:, 0, ri, :].astype(float)           # (T, nblk)
                    blk = tab.V_blocks[ar, first["S_idx"], ri, :].astype(float)
                    vb_eq[rule] = (blk0[:, picks].mean(axis=(0, 2)), blk[:, picks].mean(axis=(0, 2)))   # (N_BOOT,) each
                ent[rule] = {"n_bne": res.count,
                             "sharing_rate": [b["sharing_rate"] for b in per_bne],
                             "Lambda_rel": lam,
                             "Lambda_rel_min": min(lam) if lam else None, "Lambda_rel_max": max(lam) if lam else None,
                             "V_eq": [b["V"] for b in per_bne], "n_hired": [b["n_hired"] for b in per_bne]}
            if "SEATS" in vb_eq and "BAR" in vb_eq:
                (s0, s1), (b0, b1) = vb_eq["SEATS"], vb_eq["BAR"]
                lam_s, lam_b = (s0 - s1) / s0, (b0 - b1) / b0
                ok = lam_s > 0
                ratio = lam_b[ok] / lam_s[ok]
                ent["ratio_first"] = ent["BAR"]["Lambda_rel"][0] / ent["SEATS"]["Lambda_rel"][0] if ent["SEATS"]["Lambda_rel"][0] > 0 else None
                ent["ratio_ci95"] = [float(np.quantile(ratio, 0.025)), float(np.quantile(ratio, 0.975))] if ok.mean() > 0.95 else None
                ent["bar_loses_more_all_boot"] = bool(np.all(lam_b > lam_s))
            # worst case over equilibria for the refutation test: does fixed seats ever lose more?
            s_max, b_min = ent["SEATS"]["Lambda_rel_max"], ent["BAR"]["Lambda_rel_min"]
            ent["bar_loses_more_every_bne"] = (b_min is not None and s_max is not None and b_min > s_max)
            rec["alphas"][str(al)] = ent
            print(f"Q={Q:3d} alpha={al:.1f}: SEATS {ent['SEATS']['n_bne']} BNE loss {100 * (s_max or 0):5.2f}% | "
                  f"BAR {ent['BAR']['n_bne']} BNE loss {100 * (b_min or 0):5.2f}%  ratio {ent.get('ratio_first')}", flush=True)
        # 2.3: company value with per-hire charge kappa (alpha = 0.2, first BNE, as in X4)
        e = rec["alphas"]["0.2"]
        tau = cfg.tau
        kap = {}
        for name, k in (("0", 0.0), ("tau/2", tau / 2), ("tau", tau)):
            kap[name] = {r: {"V_noleak": rec["noleak"][r]["V"] + (tau - k) * rec["noleak"][r]["n_hired"],
                             "V_eq": e[r]["V_eq"][0] + (tau - k) * e[r]["n_hired"][0]} for r in RULES}
            kap[name]["bar_better"] = kap[name]["BAR"]["V_eq"] > kap[name]["SEATS"]["V_eq"]
        dV = e["BAR"]["V_eq"][0] - e["SEATS"]["V_eq"][0]                     # BAR minus SEATS at kappa = tau
        dN = e["BAR"]["n_hired"][0] - e["SEATS"]["n_hired"][0]
        # V_kappa difference = dV + (tau - kappa) dN; zero at kappa* = tau + dV / dN
        rec["kappa"] = {"values": kap, "dV_at_tau": dV, "d_n_hired": dN,
                        "kappa_flip": (tau + dV / dN) if abs(dN) > 1e-12 else None,
                        "kappa_flip_over_tau": ((tau + dV / dN) / tau) if abs(dN) > 1e-12 else None}
        print(f"        kappa: BAR better at 0 / tau/2 / tau: {kap['0']['bar_better']} / {kap['tau/2']['bar_better']} / "
              f"{kap['tau']['bar_better']}; extra hires under BAR {dN:+.3f}; flip at kappa = {rec['kappa']['kappa_flip']}", flush=True)
        rows.append(rec)
        del tab
    # summaries
    pos = [a for a in ALPHAS if a > 0]
    out = {"alphas": ALPHAS, "Qs": QS, "n_boot": N_BOOT, "rows": rows,
           "bar_loses_more_every_alpha_Q": all(r["alphas"][str(a)]["bar_loses_more_every_bne"] for r in rows for a in pos),
           "kappa0_seats_better_every_Q": all(not r["kappa"]["values"]["0"]["bar_better"] for r in rows),
           "seconds": time.time() - t0}
    print("cut-off loses more at every alpha > 0 and every Q (every pair of equilibria):", out["bar_loses_more_every_alpha_Q"])
    print("with kappa = 0 fixed seats give more value at every Q:", out["kappa0_seats_better_every_Q"])
    with open(os.path.join(OUT, "x4_robust.json"), "w") as f:
        json.dump(out, f, indent=1, default=float)
    print(f"X4 robustness done in {out['seconds']:.0f}s")


if __name__ == "__main__":
    main()
