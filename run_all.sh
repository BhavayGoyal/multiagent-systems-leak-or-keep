#!/usr/bin/env bash
# Regenerate every result, figure, table and number in the report from scratch.
# About 75 minutes on a 10-core laptop (X1 dominates: its nine cells run in parallel, the slowest takes ~40 min).
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

$PY -m pytest -q                                   | tee results/logs/tests.log     # 27 unit tests, ~10 s
$PY experiments/run_checks.py                      | tee results/logs/checks.log    # Table 1
$PY experiments/run_x1.py                          | tee results/logs/x1.log        # Figures 1-3   (skips finished cells)
$PY experiments/run_x2.py                          | tee results/logs/x2.log        # Table 2, Figure 3c
$PY experiments/run_x3.py                          | tee results/logs/x3.log        # 900 learning runs
$PY experiments/analyze_x3.py                      | tee results/logs/x3_analysis.log   # Table 3, Figure 4
$PY experiments/run_x4.py                          | tee results/logs/x4.log        # Figure 5
$PY experiments/run_sensitivity.py                 | tee results/logs/x5.log        # Figure 6     (skips finished settings)
$PY experiments/make_figures.py                    | tee results/logs/figures.log   # figures, tables, numbers.tex
$PY experiments/make_console_shots.py                                               # README screenshots
# PDF (needs tectonic, or any LaTeX: cd report && pdflatex main && pdflatex main)
if command -v tectonic >/dev/null 2>&1; then (cd report && tectonic main.tex); elif [ -x .tools/tectonic ]; then (cd report && ../.tools/tectonic main.tex); fi
