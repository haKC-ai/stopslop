#!/usr/bin/env bash
set -euo pipefail

choose_python() {
  for b in python3.13 python3.12 python3.11; do
    if command -v "$b" >/dev/null 2>&1; then
      echo "$b"
      return 0
    fi
  done
  echo "stopslop needs Python 3.11+" >&2
  exit 1
}

PYBIN="$(choose_python)"
VENV_DIR=".venv"

"$PYBIN" -m venv "$VENV_DIR"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip
pip install -e ".[dev]"

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example (only needed for the LLM auditor)."
fi

echo
echo "Installed into $VENV_DIR"
echo
echo "Next steps:"
echo "1) source $VENV_DIR/bin/activate"
echo "2) stopslop --file tests/fixtures/mini-shai-hulud/source.md --no-llm --format md"
