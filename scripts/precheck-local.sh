#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
base=$(dirname "$project")
tag=${1:?usage: precheck-local.sh RUN_TAG}
[[ "$tag" =~ ^[A-Za-z0-9_-]+$ ]] || exit 2
cd "$project"
python3 - "$tag" "${2:-}" <<'PY'
import json,pathlib,shutil,sys
root=pathlib.Path.cwd(); tag=sys.argv[1]; stage=root/'verification'/tag; run=root/'runs'/tag
stage.mkdir(parents=True,exist_ok=False)
shutil.copytree(root/'tt/precheck',stage/'precheck',ignore=shutil.ignore_patterns('reports','__pycache__'))
(stage/'precheck/reports').mkdir()
(stage/'tech').symlink_to(root/'tt/tech',target_is_directory=True)
shutil.copy2(root/'info.yaml',stage/'info.yaml')
if sys.argv[2]:
 state=json.loads(pathlib.Path(sys.argv[2]).read_text()); files=[(pathlib.Path(state['gds']),'tt_um_cokane_soc.gds'),(pathlib.Path(state['lef']),'tt_um_cokane_soc.lef'),(pathlib.Path(state['pnl']),'tt_um_cokane_soc.v')]
else:
 files=[(run/'final/gds/tt_um_cokane_soc.gds','tt_um_cokane_soc.gds'),(run/'final/lef/tt_um_cokane_soc.lef','tt_um_cokane_soc.lef'),(run/'final/pnl/tt_um_cokane_soc.pnl.v','tt_um_cokane_soc.v')]
for source,name in files: shutil.copy2(source,stage/name)
PY
unset VERILATOR_ROOT YOSYS_DATDIR GHDL_PREFIX PYTHONHOME PYTHONEXECUTABLE LD_LIBRARY_PATH
export PATH=/usr/local/bin:/usr/bin:/bin
cd "$base/tools/librelane-devshell"
exec ./AppRun bash -c 'set -e; cd "$1"; source .precheck-venv/bin/activate; export PDK_ROOT=$(python -c "import json; print(json.load(open(\"runs/$2/resolved.json\"))[\"PDK_ROOT\"])") PDK=sky130A QT_QPA_PLATFORM=offscreen OMP_NUM_THREADS=2; cd "verification/$2/precheck"; exec python precheck.py --gds "$1/verification/$2/tt_um_cokane_soc.gds" --tech sky130A' bash "$project" "$tag"
