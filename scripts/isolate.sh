#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
STORE="${AICA005_ISOLATION_DIR:-$HOME/.local/share/aica005-django-agent-workshop/isolation}"
mkdir -p "$STORE"
STORE="$(cd "$STORE" && pwd -P)"
case "$STORE/" in "$ROOT/"*) echo "Isolation store must be outside the lab checkout." >&2; exit 1;; esac

case "${1:-}" in
  before-b)
    [[ -f "$ROOT/reports/A/evidence.zip" ]] || { echo "A evidence ZIP missing; export it before B." >&2; exit 1; }
    [[ ! -e "$STORE/A.backup" && ! -e "$STORE/A.archived" ]] || { echo "A archive already exists; restore or review it first." >&2; exit 1; }
    cp -a "$ROOT/reports/A" "$STORE/A.backup"
    diff -r "$ROOT/reports/A" "$STORE/A.backup" >/dev/null || { echo "A backup verification failed; workspace unchanged." >&2; exit 1; }
    mv "$ROOT/reports/A" "$STORE/A.archived"
    [[ ! -e "$ROOT/reports/A" ]] || { echo "A evidence remains visible in the workspace." >&2; exit 1; }
    echo "A evidence archived outside lab checkout; backup verified. Resetting Django."
    bash "$ROOT/scripts/reset.sh"
    bash "$ROOT/scripts/preflight.sh" --check
    ;;
  after-b)
    [[ -f "$ROOT/reports/B/evidence.zip" ]] || { echo "B evidence ZIP missing; verify and package B first." >&2; exit 1; }
    [[ -d "$STORE/A.archived" && -d "$STORE/A.backup" ]] || { echo "Verified A archive missing." >&2; exit 1; }
    [[ ! -e "$ROOT/reports/A" ]] || { echo "A report destination already exists; refusing overwrite." >&2; exit 1; }
    diff -r "$STORE/A.archived" "$STORE/A.backup" >/dev/null || { echo "A archive differs from verified backup." >&2; exit 1; }
    cp -a "$STORE/A.archived" "$ROOT/reports/A"
    diff -r "$STORE/A.backup" "$ROOT/reports/A" >/dev/null || { echo "A restoration failed; retained outside backup." >&2; exit 1; }
    echo "A evidence restored byte-for-byte. Comparing A and B."
    python3 "$ROOT/scripts/results.py" compare
    ;;
  *) echo "Usage: bash scripts/isolate.sh before-b|after-b" >&2; exit 2;;
esac
