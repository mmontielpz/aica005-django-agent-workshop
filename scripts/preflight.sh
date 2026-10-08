#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DJANGO="$ROOT/workspace/django"
BASE=93e892bb645b16ebaf287beb5fe7f3ffe8d10408
MODE="${1:---check}"

if [[ "$MODE" == --setup ]]; then
  if [[ ! -d "$DJANGO/.git" ]]; then
    mkdir -p "$ROOT/workspace"
    git clone --filter=blob:none --no-checkout https://github.com/django/django.git "$DJANGO"
    git -C "$DJANGO" checkout --detach "$BASE"
  fi
  if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
    python -m venv "$ROOT/.venv"
  fi
  "$ROOT/.venv/bin/python" -m pip install --disable-pip-version-check \
    'pip==23.3.2' 'setuptools==65.6.3' 'wheel==0.42.0' \
    'pytz==2023.3' 'sqlparse==0.4.4' 'tblib==2.0.0'
  "$ROOT/.venv/bin/python" -m pip install --disable-pip-version-check --no-deps -e "$DJANGO"
elif [[ "$MODE" != --check ]]; then
  echo "Usage: bash scripts/preflight.sh [--setup|--check]" >&2
  exit 2
fi

[[ -d "$DJANGO/.git" ]] || { echo "Django checkout missing. Run --setup." >&2; exit 1; }
[[ "$(git -C "$DJANGO" remote get-url origin)" == "https://github.com/django/django.git" ]] || { echo "Unexpected Django remote." >&2; exit 1; }
[[ "$(git -C "$DJANGO" rev-parse HEAD)" == "$BASE" ]] || { echo "Wrong Django baseline." >&2; exit 1; }
[[ -z "$(git -C "$DJANGO" status --porcelain)" ]] || { echo "Django checkout is not clean; use scripts/reset.sh before an experiment." >&2; exit 1; }
[[ -x "$ROOT/.venv/bin/python" ]] || { echo "Virtual environment missing. Run --setup." >&2; exit 1; }
"$ROOT/.venv/bin/python" -c 'import django, sys; assert sys.version_info[:2] == (3, 7), sys.version; print("Python", sys.version.split()[0], "Django", django.get_version())'
echo "Preflight PASS: django/django at $BASE; clean checkout."
