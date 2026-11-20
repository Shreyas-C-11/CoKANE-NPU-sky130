#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p evidence/cokane verification/inference
source .venv/bin/activate
python scripts/build-inference.py > evidence/cokane/inference-build.log 2>&1
gcc -std=c11 -Wall -Wextra -Werror -O2 -fPIC -shared -DCOKANE_HOST_TEST -Ifirmware firmware/cokane_scheduler.c firmware/inference_reference.c test_inference/host_backend.c -o verification/inference/scheduler-host.so
python scripts/test_scheduler_host.py "$PWD/verification/inference/scheduler-host.so" > evidence/cokane/scheduler-host.log 2>&1
if [[ "${SIM:-verilator}" == verilator ]]; then
 project="$PWD"
 unset VERILATOR_ROOT YOSYS_DATDIR PYTHONHOME PYTHONEXECUTABLE LD_LIBRARY_PATH
 (cd ../tools/librelane-devshell; ./AppRun bash -c 'set -eu; cd "$1"; source .venv/bin/activate; make -C test_inference SIM=verilator SIM_BUILD="$1/verification/inference/sim-verilator" WAVES=0' bash "$project") > evidence/cokane/inference-rtl.log 2>&1
else
 make -C test_inference SIM=icarus ICARUS_BIN_DIR="$PWD/scripts" > evidence/cokane/inference-rtl.log 2>&1
fi
python -m cocotb_tools.check_results test_inference/results.xml
cp test_inference/results.xml evidence/cokane/inference-results.xml
python scripts/collect-inference.py
