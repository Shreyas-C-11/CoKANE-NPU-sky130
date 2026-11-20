#!/bin/bash
# Feasibility mapping, not placement, timing closure or signoff.
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
cd "$project"
mkdir -p evidence/cokane verification/cokane-synth
unset VERILATOR_ROOT YOSYS_DATDIR PYTHONHOME PYTHONEXECUTABLE LD_LIBRARY_PATH
export PATH=/usr/local/bin:/usr/bin:/bin
cd ../tools/librelane-devshell
exec ./AppRun bash -c 'set -euo pipefail; cd "$1"; source ../ttvenv/bin/activate; export PYTHONPATH=../pyextra; exec python scripts/synth-cokane.py' bash "$project"
