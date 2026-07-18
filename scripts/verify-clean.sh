#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
python3 -m unittest discover -v
python3 scripts/verify-public-evidence.py
python3 scripts/demo.py
echo "Clean verification passed."
