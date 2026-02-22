#!/usr/bin/env bash
# Package the merged HF model into a zip for distribution/backups.
# Usage: ./scripts/package_model.sh outputs/ald01-merged
set -euo pipefail
MODEL_DIR=${1:-outputs/ald01-merged}
OUT_ZIP="${MODEL_DIR%/}.zip"
if [ ! -d "$MODEL_DIR" ]; then
  echo "Model directory not found: $MODEL_DIR"
  exit 1
fi
rm -f "$OUT_ZIP"
zip -r "$OUT_ZIP" "$MODEL_DIR"
echo "Packaged model into $OUT_ZIP"
