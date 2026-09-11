#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
python -m ruthless_pipeline.platform_runtime --open
