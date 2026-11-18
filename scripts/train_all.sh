#!/usr/bin/env bash
# Full reproducible pipeline: preprocessing -> baselines -> NeuMF -> evaluation.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$ROOT/venv/bin/python"
cd "$ROOT"

echo "== 1/7 preprocessing =="        && $PY -m ml.preprocessing.run_preprocessing
echo "== 2/7 evaluation candidates ==" && $PY -m ml.evaluation.build_candidates
echo "== 3/7 matrix factorization ==" && $PY -m ml.training.train_mf
echo "== 4/7 NeuMF =="                && $PY -m ml.training.train_neumf
echo "== 5/7 rating predictor =="     && $PY -m ml.training.train_rating
echo "== 6/7 evaluation =="           && $PY -m ml.evaluation.evaluate_all
echo "== 7/7 hybrid re-ranking =="    && $PY -m ml.evaluation.evaluate_hybrid
echo "Done. Artifacts in $ROOT/artifacts"
