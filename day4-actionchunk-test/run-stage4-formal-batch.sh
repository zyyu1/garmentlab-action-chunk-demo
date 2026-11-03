#!/usr/bin/env bash
# Canonical E entrance. The A5 release gate runs before initial generation.
set -euo pipefail
base=$(cd "$(dirname "$0")" && pwd)
candidate="$base/stage4-a5-rc1/app"
[[ -f "$candidate/a5_entry.py" ]] || { echo "E BLOCKED: deploy the A5 candidate first" >&2; exit 2; }
exec bash "$candidate/run-stage4-formal-batch.sh" "$candidate/stage4-heldout-seeds.json" "${2:-formal-a5}"
