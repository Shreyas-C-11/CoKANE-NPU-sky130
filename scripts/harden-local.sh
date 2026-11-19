#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
base=$(dirname "$project")
cd "$base/tools/librelane-devshell"
exec ./AppRun bash -c 'set -e; cd "$1"; source "$2/ttvenv/bin/activate"; export PYTHONPATH="$2/pyextra" PDK=sky130A PDK_ROOT="$2/pdk"; python ./tt/tt_tool.py --create-user-config; exec python ./tt/tt_tool.py --harden --no-docker' bash "$project" "$base"
