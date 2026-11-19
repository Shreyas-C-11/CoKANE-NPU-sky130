#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate
make -C test ICARUS_BIN_DIR="$PWD/scripts" "$@"
python -m cocotb_tools.check_results test/results.xml
