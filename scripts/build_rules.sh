#!/usr/bin/env bash
# Exercise the REAL CodeGuard tooling on our authored rules:
#   1. copy hello-spec rules into the CodeGuard repo's custom-rule source path
#   2. validate them with CodeGuard's validator
#   3. convert them to all IDE/agent bundle formats
#   4. copy the bundles into build/ and clean up the CodeGuard working tree
#
# Uses `uv run` if available, otherwise plain python3 (pyyaml required).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CG="$ROOT/project-codeguard"
SRC="$CG/sources/rules/hellospec"
OUT="$ROOT/build/codeguard-bundles"

if [ ! -d "$CG/src" ]; then
  echo "ERROR: project-codeguard submodule not found at $CG" >&2
  echo "Run: git submodule update --init --recursive" >&2
  exit 1
fi

run_py() {
  if command -v uv >/dev/null 2>&1; then ( cd "$CG" && uv run python "$@" ); \
  else ( cd "$CG" && python3 "$@" ); fi
}

echo ">> staging rules into $SRC"
rm -rf "$SRC"; mkdir -p "$SRC"
cp "$ROOT"/rules/codeguard-*.md "$SRC"/

cleanup() {
  rm -rf "$SRC"
  # restore any CodeGuard working-tree files the converter regenerates
  git -C "$CG" checkout -- skills/ 2>/dev/null || true
}
trap cleanup EXIT

echo ">> validating with CodeGuard's validator"
run_py src/validate_unified_rules.py sources/rules/hellospec

echo ">> converting to IDE/agent bundles -> $OUT"
mkdir -p "$ROOT/build"
run_py src/convert_to_ide_formats.py --source core hellospec -o "$OUT"

echo ">> done. Bundles in $OUT"
ls "$OUT" 2>/dev/null || true
