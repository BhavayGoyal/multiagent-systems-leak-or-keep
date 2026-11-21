#!/usr/bin/env bash
# Regenerate every result, figure, table and number in the report from scratch.
# About 3 hours on a 16 GB laptop with  X1_WORKERS=2 X3_WORKERS=2 CCE_WORKERS=1  (measured: 2 h 43 min for the steps up
# to X4, before the Phase 1 and X5 steps were added; the CCE programs and X1 dominate).  The CCE programs need 4 to 6 GB
# each for two friend groups (set CCE_WORKERS higher only if you have the memory; with less than about 8 GB free use
# X1_WORKERS=1, or HiGHS fails with "MemoryError: std::bad_alloc").
# NOTE: run_x1.py and run_cce.py skip cells whose result file already exists, so in a clone delete results/ first, then
# restore the optional cross-check inputs: git checkout -- results/x1/independent
set -euo pipefail
cd "$(dirname "$0")"
# Python: $PY if set, else the project venv (Linux/macOS or Windows layout), else python on PATH.
if [ -z "${PY:-}" ]; then
  if [ -x .venv/bin/python ]; then PY=.venv/bin/python
  elif [ -x .venv/Scripts/python.exe ]; then PY=.venv/Scripts/python.exe
  else PY=python; fi
fi
export MPLCONFIGDIR="$PWD/.mplconfig"
mkdir -p results/logs "$MPLCONFIGDIR"

$PY -m pytest -q                                   | tee results/logs/tests.log     # 43 unit tests, ~15 s
$PY experiments/run_checks.py                      | tee results/logs/checks.log    # Table 1 (7 min on a first run: builds payoff tables)
$PY experiments/run_x1.py                          | tee results/logs/x1.log        # Figures 1-3   (skips finished cells)
$PY experiments/run_cce.py ${CCE_WORKERS:-1}        | tee results/logs/x1_cce.log    # CCE programs for E0 and E2 (E1 is in run_x1)
$PY experiments/run_support.py                     | tee results/logs/x1_support.log # dominance + support enumeration
$PY experiments/run_x2.py                          | tee results/logs/x2.log        # Table 2, Figure 3c
$PY experiments/run_x3.py                          | tee results/logs/x3.log        # 1,080 learning runs
$PY experiments/analyze_x3.py                      | tee results/logs/x3_analysis.log   # Table 3, Figure 4
$PY experiments/run_h1.py                          | tee results/logs/h1.log        # H1 pivotality
$PY experiments/run_baselines.py                   | tee results/logs/baselines.log # needs X3
$PY experiments/run_explanations.py                | tee results/logs/explanations.log  # needs X3
$PY experiments/run_e2_bias.py                     | tee results/logs/e2_bias.log
$PY experiments/run_x4.py                          | tee results/logs/x4.log        # Figure 5
$PY experiments/run_sensitivity.py                 | tee results/logs/x5.log        # X5, Figure 6  (skips finished settings)
# Optional independent cross-check of the CCE programs (a second implementation; about 2 h, up to 6 GB per worker).
# make_figures.py uses its files when they exist and asserts that they agree with run_cce.py.
# $PY experiments/run_cce_e0e2.py                  | tee results/logs/x1_cce_e0e2.log
$PY experiments/make_figures.py                    | tee results/logs/figures.log   # figures, tables, numbers.tex
$PY experiments/make_console_shots.py                                               # README screenshots
# PDF (needs tectonic, or any LaTeX: cd report && pdflatex main && pdflatex main)
if command -v tectonic >/dev/null 2>&1; then (cd report && tectonic main.tex); elif [ -x .tools/tectonic ]; then (cd report && ../.tools/tectonic main.tex); fi
