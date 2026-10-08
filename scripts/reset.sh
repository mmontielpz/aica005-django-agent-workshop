#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DJANGO="$ROOT/workspace/django"
BASE=93e892bb645b16ebaf287beb5fe7f3ffe8d10408
[[ -d "$DJANGO/.git" ]] || { echo "Django checkout missing." >&2; exit 1; }
[[ "$(git -C "$DJANGO" rev-parse --show-toplevel)" == "$DJANGO" ]] || { echo "Unexpected checkout path." >&2; exit 1; }
[[ "$(git -C "$DJANGO" remote get-url origin)" == "https://github.com/django/django.git" ]] || { echo "Unexpected Django remote." >&2; exit 1; }

echo "Resetting only $DJANGO. Save candidate evidence first."
git -C "$DJANGO" reset --hard "$BASE"
git -C "$DJANGO" checkout --detach "$BASE"
git -C "$DJANGO" clean -fd
bash "$ROOT/scripts/preflight.sh" --check
