#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
tag=${1:-baseline-$(date -u +%Y%m%d-%H%M%S)}
exec "$project/scripts/harden-named.sh" "$tag"
