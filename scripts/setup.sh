#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
command -v python3 >/dev/null
command -v git >/dev/null
python3 -c 'import sys; assert sys.version_info >= (3, 11), "Python 3.11+ required"'
python3 -m unittest discover -q
echo "Rehearsal is ready. Run ./scripts/start.sh"
