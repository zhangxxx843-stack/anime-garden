#!/usr/bin/env bash
# Requires Cangjie 1.0.5 on PATH. Runs host-side pure algorithm tests only.
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$project_dir/target/core-tests"
cjc --test "$project_dir"/src/shopping/*.cj -o "$project_dir/target/core-tests/shopping-tests"
"$project_dir/target/core-tests/shopping-tests" --no-color
