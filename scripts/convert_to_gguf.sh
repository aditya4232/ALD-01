#!/usr/bin/env bash
# Helper: convert HF merged model to GGUF using llama.cpp tools.
# Usage: ./scripts/convert_to_gguf.sh outputs/ald01-merged /path/to/llama.cpp/bin
# Arguments:
#  $1 : HF model dir (default outputs/ald01-merged)
#  $2 : path to llama.cpp bin dir containing "convert" and "quantize" tools (optional)

set -euo pipefail
HF_DIR=${1:-outputs/ald01-merged}
LLAMA_BIN_DIR=${2:-}
OUT_DIR="${HF_DIR}_gguf"
mkdir -p "$OUT_DIR"

if [ ! -d "$HF_DIR" ]; then
  echo "HF model directory not found: $HF_DIR"
  exit 1
fi

echo "Converting HF model at $HF_DIR to GGUF format (intermediate files in $OUT_DIR)"

# Option A: If you have the 'transformers-cli' or 'convert' script from llama.cpp/python-gguf,
# use it here. These commands are examples and might require you to adapt paths.

if [ -n "$LLAMA_BIN_DIR" ] && [ -x "$LLAMA_BIN_DIR/convert" ]; then
  echo "Using llama.cpp convert tool at $LLAMA_BIN_DIR/convert"
  # Try common argument patterns; if the first fails, try a fallback.
  if "$LLAMA_BIN_DIR/convert" --help >/dev/null 2>&1; then
    # Preferred attempt: positional model dir + outfile
    if "$LLAMA_BIN_DIR/convert" "$HF_DIR" "$OUT_DIR/model.gguf"; then
      echo "GGUF saved to $OUT_DIR/model.gguf"
      exit 0
    fi
    # Fallback: try --outfile style
    if "$LLAMA_BIN_DIR/convert" --outfile "$OUT_DIR/model.gguf" --model "$HF_DIR"; then
      echo "GGUF saved to $OUT_DIR/model.gguf"
      exit 0
    fi
    echo "convert tool ran but conversion failed with attempted argument patterns."
    exit 1
  else
    echo "convert tool exists but could not be queried for --help"
    exit 1
  fi
else
  echo "llama.cpp convert tool not provided or not executable."
  echo "Please follow scripts/convert_gguf.md for manual instructions to convert and quantize."
  exit 1
fi
