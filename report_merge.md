# Merge report: where the project stands after merging Chaitanya's and Bhavay's work

This report has four jobs:
1. Record what the merge of the two lines of work did.
2. Check the merged repository from end to end, saying what was checked and what was found.
3. List everything done on the project so far, by whom, against the proposal.
4. Say how the plan changed as a result.

It is written for the four of us. Every number below comes from the result files or from a check run while writing
it, and the checks can be re-run with the commands in section 8.

**In one paragraph.** Branch `merge-bhavay` (pushed to `origin`, Bhavay's repository) now holds all the work: the
original submission (Vishnu), the review fixes and Phases 0–1 (Chaitanya), and Bhavay's five parallel commits (X5
sensitivity, an independent CCE implementation, an E0 coordination measure, setup fixes). The merged repository passes
every check I ran:
- 42 tests pass;
- regenerating every table and macro changes no committed file;
- the report builds at 12 pages with no unresolved references;
- Bhavay's X5 results are reproduced exactly by the merged code;
- the two CCE implementations agree on all 212 rows;
- my pivotality measure independently confirms his surprising K = 3 result.

The audit found five problems: one inconsistency of units in the report (not yet fixed; it needs a wording decision),
one wrong number in three documents (fixed), stale commit hashes in two documents (fixed), and two stale descriptions
of the branches (fixed in `plan.md`). The project's core and target deliverables are complete. The open items are the
stretch target `n = 8`, a few robustness checks, the E0 mechanism, CCEs for X2, and the final write-up.

---

## 1. Where everything is

| Branch | Contents | On `origin` (Bhavay's repo)? |
|---|---|---|
| **`merge-bhavay`** | **everything** (all work below, merged) | **yes** (`3353bdc`) |
| `main` (local) | original submission + review fixes + Phase 0 | no (origin's `main` is Bhavay's `be00bff`) |
| `phase-1` (local) | + Phase 1, without Bhavay's work | no |
| `origin/main`, `origin/improvements` | original submission + Bhavay's five commits | — |

The report cites the team repository `Vish-Overflows/multiagent-systems-leak-or-keep` (`\RepoURL` in
`report/main.tex`). None of this work is there yet.

## 2. Timeline of the work

| # | Work | By | Commits |
|---|---|---|---|
| 1 | Original submission: simulator, exact solvers, five learners, X1–X4, report | Vishnu (and the team, per the proposal's split) | `3c7d73f` |
| 2 | Review items 1–8 (`fix.md`): NumPy ≥ 2.0, X4 caveat, regret column, refutation criteria, near-equilibrium counts, CCE for E0/E2, dominance + support enumeration, fairness bootstrap, honest leak-aware learner, Model-based UCB | Chaitanya (with Claude) | `6ee0e8c` … `e0898ed` (6) |
| 3 | Phase 0: PDF, `uv.lock`, `.gitattributes`, clean-clone reproduction (`report_p0.md`) | Chaitanya | `2c194ae`, merge `77e8f35`, `41345c4` |
| 4 | Phase 1: six small gaps closed (`report_p1.md`) | Chaitanya | `b6b51cd`, `96e3f2b`, `f1abb4f` |
| 5 | In parallel, on the original submission: NumPy ≥ 2.0 + Windows `run_all.sh`; README second-machine check; `frac_within_c` (E0 coordination); **X5 sensitivity**; **CCE for E0/E2** | Bhavay | `6a2a0d2`, `8a98313`, `f9e4155`, `146cb72`, `be00bff` |
| 6 | Merge of 4 and 5, plan update | Chaitanya | `05d4452`, `3353bdc` |

In total there are 20 commits: 14 by Chaitanya, 5 by Bhavay and 1 by Vishnu. Commit hashes before 6 were changed once by
a history rewrite that removed co-author trailers. `report_p0.md` and `report_p1.md` now quote the current hashes.

## 3. What the merge did

### Where the two lines overlapped and how it was resolved

| Topic | Chaitanya's side | Bhavay's side | Resolution |
|---|---|---|---|
| CCE programs for E0 and E2 | `run_cce.py`, resumable, asserts per row that every pure equilibrium lies inside the CCE interval and that the rebuilt table reproduces X1 | `run_cce_e0e2.py`, written independently, also stores the pure range and a summary | **They agree on all 212 rows (largest difference 0.0).** Same file names, different formats, so `run_cce.py` stays canonical (`results/x1/x1_cce_*.json`) and his files moved to `results/x1/independent/` (his script now writes there). `make_figures.py` asserts that the two give the same counts and intervals; the report says a second implementation confirms them |
| E0 CCE finding in the report (§5.1) | 55 / 106 single points, 48 wider, up to 42 points wide, the 4-equilibria example | 48 wider, up to 33 above / 8 below the pure range, star and two-groups maxima, pairs untouched | one paragraph with both sets of facts |
| NumPy ≥ 2.0 | yes | yes | same change |
| `run_all.sh` | worker settings, Phase 1 steps | `python`-on-PATH fallback, X5 step | combined; his independent CCE step is commented out (optional, 2 h) |
| `.gitattributes` | `* text=auto`, LF scripts, binaries | LF scripts | mine (a superset) |
| README | Phase 0/1 sections | X5 results, second-machine check | combined; two of his rows now name the canonical CCE files |
| Table 4, H1 row | independent pivotality numbers | "α\* follows ℓ in all X5 settings; at K = 3 average types are pivotal" | both |
| Deviations and limits (§5.6) | my list | "tightly in E1/E2, loosely in E0"; X5 limit | mine plus his phrases; the limit now also names c and the hub position as not varied |
| Contribution table | — | — | **Bhavay's row now credits X5 and the CCE cross-check.** Please confirm |
| Generated files (`numbers.tex`, `numbers.json`, `x3_summary.json`, `x3_analysis.log`, PDF) | | | regenerated from the merged sources, not text-merged. Git's text merge of `x3_summary.json` had silently missed his new field for the sixth learner |

### What the merge added to the report
- §5.5 "How robust is the staircase? (X5)" with Figure 6.
- His E0 coordination sentence in §5.3: in E0 under a cut-off, every learner's settled profile is an exact equilibrium
  in 0 % of runs but within one message cost of one in 100 %. The two counts coincide in all 30 other learner-setting
  pairs.
- The merged §5.1 CCE paragraph.

The report went from 11 to 12 pages.

## 4. The audit: what was checked

| # | Check | Result |
|---|---|---|
| A1 | Unit tests | **42 pass** (37 test functions; parametrised) |
| A2 | Regenerate every figure, table and macro (`make_figures.py`) and diff against the committed files | **no drift**: no committed table, macro or number changes (figure binaries differ only by rendering) |
| A3 | Any macro name assigned twice with different values (instrumented run of `make_figures.py`) | **none** (842 macros) |
| A4 | PDF build (`tectonic --keep-logs`) | **12 pages; 0 overfull boxes, 0 undefined references, 0 dropped floats, no `??`** |
| A5 | Every macro used in `main.tex` is defined; braces balance; table column counts | all pass |
| A6 | Every script called by `run_all.sh` exists | yes; the only script not called is `compare_with_committed.py`, which is run by hand on purpose |
| A7 | Bhavay's X5, re-run with the merged code (2 workers, 45 min) | **all 8 result files identical** to his (largest relative difference 0.0) |
| A8 | Bhavay's X3 numbers (30 cells, five learners) after regeneration | **identical** |
| A9 | The two CCE implementations, row by row | **identical on all 212 rows** |
| A10 | 42 headline numbers typed by hand in the README checked against `results/numbers.json` | 41 match; **1 wrong** (see P2) |
| A11 | Bhavay's K = 3 claim ("average types are the pivotal ones") against my independent pivotality measure | **confirmed** (table below) |
| A12 | Scan of all documents for stale statements (test counts, learner counts, page counts, section numbers, branch names, "not measured", "did not test") | 3 problems found (P3–P5) |
| A13 | Clean-clone reproduction | done before the merge (`report_p0.md`: 2 h 43 min, every JSON/NPZ/LaTeX identical). **Not repeated after the merge**: the merged code reproduces X5 (A7) and X3 (A8) and adds no new code to X1–X4, but a full rerun is still due in Phase 6 |

**A11 in detail.** Fresh simulation with nobody sharing, 1 million days per K: the share of days on which a type holds the
last seat, next to X5's own loss and break-even friendliness.

| K (of 6) | P(holds last seat): weak / average / strong | X5 own loss ℓ (tell all later friends, points) | X5 α\* | Order (all three) |
|---|---|---|---|---|
| 1 | 0.9 / 8.5 / 40.7 % | 0.14 / 1.04 / 2.51 | 0.05 / 0.22 / 0.57 | weak < average < strong |
| 2 | 3.6 / 17.9 / 28.5 % | 0.57 / 2.23 / 2.41 | 0.10 / 0.32 / 0.38 | weak < average < strong |
| 3 | 9.0 / **23.6** / 17.4 % | 1.24 / **2.64** / 1.48 | 0.20 / **0.36** / 0.22 | weak < strong < **average** |

So H1 holds at every K when pivotality is measured independently of the loss. The type that is most often at the
margin always needs the most friendliness, and *which* type that is depends on K. This is a stronger statement than the
report now makes, and it is cheap to add (plan item M.2).

## 5. Problems found

| # | Problem | Status |
|---|---|---|
| **P1** | **Inconsistent units in the report.** §5.1 gives the own loss *per friend told* (weak / average / strong 0.38 / 1.49 / 1.60 points). §5.5 (from X5) gives it *for telling all later friends* (K = 3: 1.24 / 2.64 / 1.48), without saying so; at the baseline that measure is 0.57 / 2.23 / 2.41. Both are called "points", so a reader would conclude that a weak type's loss tripled at K = 3; in consistent units it about doubled | **open**, plan item M.1. It needs a wording choice: state the unit in §5.5 and give the baseline value, or convert X5 to per friend |
| P2 | P(last seat \| strong) was written as **28.6 %** in the README, `plan.md` and `report_p1.md`; the true value is 0.28545, i.e. **28.5 %**, which the report (macro) prints. I rounded twice by hand | **fixed** in the three files. The Phase 1 commit *message* still says 28.6; history was not rewritten for this |
| P3 | `report_p0.md` and `report_p1.md` quoted commit hashes from before the history rewrite (`0e39b8a`, `5186232`, `4c70827`, `8adc1f5`, `6ceb6b6`), which no longer exist | **fixed** (mapped by commit subject to `2c194ae`, `77e8f35`, `41345c4`, `b6b51cd`, `96e3f2b`) |
| P4 | `plan.md` still described the pre-merge branches (`phase-1` "not merged") | **fixed** (rewritten status, section 7) |
| P5 | `report_p0.md` §3 names the remote as `Vish-Overflows/...`; at the time of the push it was the fork `Tree-08/...`, and now it is `BhavayGoyal/...` | left as a historical record; this report states the current remotes |

Not problems, but worth knowing:
- `run_cce.py` and `run_cce_e0e2.py` duplicate work on purpose; only the first is in `run_all.sh`.
- The committed `results/logs/x5.log` comes from a pass that only re-summarised existing files ("X5 done in 1s"), so it
  does not show the run time. His README gives 26 min (the script's default is 4 workers); my regression re-run took
  45 min with 2.
- The only "plausible reason, which we did not test" left in the report is the E0 redundancy explanation (plan 3.1).

## 6. Everything done so far, against the proposal

### Deliverables

| Proposal deliverable | Status | Where |
|---|---|---|
| Verified simulator (E0–E2, networks, checks) | **done** | `leakgame/`, Table 1, 42 tests |
| X1: equilibria across rule × α × network × leak model | **done**: 378 games exhaustively; complete network by deviation tests (n = 4 solved) | §5.1, Figures 1–3 |
| X1: CCEs | **done** for E0, E1, E2 (two implementations agree) | §5.1 |
| Mixed equilibria (replicator + support enumeration) | **partly**: replicator everywhere; dominance on all networks (solves 311 / 378); support enumeration on pairs only (3 mixed equilibria found) | §4.2, §5.1 |
| X2: utility types and mixed populations | **done**; fairness bootstrap fixed | §5.2, Table 2 |
| X2: CCEs | **not done** (no CCE programs were run for the X2 utilities) | — |
| X3: learners, regret, CCE gap, rounds to 90 % | **done**, six learners, 1,080 runs, per-setting tests | §5.3, Table 3, Figure 4, Table 5 |
| Model-based learner | **done in reduced form** (Model-based UCB; plus leak-aware UCB) | §4.3, §5.3 |
| Baselines (nobody, everybody, random, equilibrium, leak-free) | **done** | §5.3–5.4, Table 6 |
| X4: company loss vs bank size | **done**, with random sharing and the everyone-tells comparison | §5.4, Figure 5 |
| Robustness | **partly**: X5 covers Δ, σ, K one at a time | §5.5, Figure 6 |
| Stretch target n = 8 | **not done** | — |
| Report with verdicts on H1–H5 | **done** (12 pages) | `report/main.pdf` |

### Hypotheses (Table 4, judged by the refutation criteria fixed in the proposal)

| | Verdict | Evidence added since the original submission |
|---|---|---|
| H1 | supported | independent pivotality (Phase 1); holds in all X5 settings; confirmed at K = 1, 2, 3 with the independent measure (A11) |
| H2 | refuted once (E0), holds in all 126 E1/E2 comparisons and all 140 X5 comparisons | refutation criterion applied (review item 4); X5 |
| H3 | supported | — |
| H4 | "faster": supported (Model-based UCB); "nears the CCE set": weak (the gap falls in 36 / 36 tests but stays the size of the payoff gaps) | Model-based UCB; per-setting tests |
| H5 | supported at α = 0.2; the ratio falls from 8–12× to 2.5–4.4× if everyone tells | X4 decomposition, random sharing |

### Plan items (`plan.md`)

| Phase | Done | Partly done | Open |
|---|---|---|---|
| 0 Close out | 0.1, 0.2, 0.3, 0.4 | — | page limit (D1) |
| 1 Quick wins | 1.1–1.6 | — | 1.5(e) is 3.1 |
| 2 Robustness | — | 2.1 (Δ, σ, K by X5) | 2.1 c and hub; 2.2 X4 at other α; 2.3 company-value definition; 2.4 |
| 3 E0 | — | 3.1 (finding confirmed twice), 3.2 (`frac_within_c`) | 3.1 test of the explanation; 3.2 learners vs the CCE interval; 3.3 proposition |
| 4 Scope | — | — | 4.1 n = 8; 4.2 support enumeration beyond 2 actions; 4.3 learning elsewhere |
| 5 Optional | — | — | all |
| 6 Write-up | — | report updated through the merge | 6.1–6.4 |

## 7. How the plan changed

`plan.md` was updated as follows:
1. **The status section was rewritten for the merged state.** It has one table of every item, each marked done / partly
   done / open, and says who did what.
2. **A new short phase "M: fixes from the merge audit"** comes before Phase 2:
   - M.1 the units inconsistency P1;
   - M.2 add the K-dependence of pivotality (A11) to the report;
   - M.3 decide which repository is final and update `\RepoURL`;
   - M.4 fast-forward `main` to `merge-bhavay`.
3. **Phase 2.1 shrinks** to what X5 did not cover (the message cost c and the hub position), plus the joint
   sweep 2.4.
4. **3.1 and 3.2 are marked partly done**, with what remains.
5. **A new item 2.5, "CCEs for the X2 utilities"**, closes the last core-deliverable gap from the proposal.
6. **The phase map, the decisions table and the run-time table were updated** (X5 times, 12 pages, CCE cross-check).

## 8. How to verify this report

```bash
python -m pytest -q                                        # A1: 42 pass
python experiments/make_figures.py && git status --short    # A2: only figure binaries / figures.log change
cd report && ./tectonic.exe --keep-logs main.tex            # A4: 12 pages; grep Overfull / undefined in main.log
python experiments/run_sensitivity.py                       # A7: delete results/x5 first; compare with git (45 min, 2 workers via X5_WORKERS=2)
python -c "from leakgame.config import GameConfig; from leakgame.analysis import pivotality_by_type as p; print([round(100*x,1) for x in p(GameConfig(K=3), n_days=1_000_000)['P_rank_K']])"   # A11
```

## 9. Decisions that are still yours

- The page limit and deadline (the report is 12 pages).
- Whether there is a presentation.
- Which repository is final (`\RepoURL`).
- Whether `merge-bhavay` becomes `main` here and on `origin`.
- Which open phases are in scope.
- Confirm the Contribution-table credit for Bhavay.
- How to word the fix for P1.
