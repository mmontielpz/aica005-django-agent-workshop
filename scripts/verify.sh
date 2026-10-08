#!/usr/bin/env bash
set -u -o pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DJANGO="$ROOT/workspace/django"
PY="$ROOT/.venv/bin/python"
RUN="${1:-}"
if [[ ! "$RUN" =~ ^(A|B|BASELINE|READINESS)$ ]]; then
  echo "Usage: bash scripts/verify.sh A|B|BASELINE|READINESS" >&2
  exit 2
fi
[[ -x "$PY" && -d "$DJANGO/.git" ]] || { echo "Run scripts/preflight.sh --setup first." >&2; exit 2; }
REPORT="$ROOT/reports/$RUN"
mkdir -p "$REPORT"
printf 'check\texit_code\tseconds\tcommand\n' > "$REPORT/status.tsv"

run_check() {
  local name="$1" command="$2" start code elapsed
  start="$(date +%s)"
  echo "Running $name: $command"
  bash -c "$command" 2>&1 | tee "$REPORT/$name.log"
  code="${PIPESTATUS[0]}"
  elapsed="$(( $(date +%s) - start ))"
  printf '%s\t%s\t%s\t%s\n' "$name" "$code" "$elapsed" "$command" >> "$REPORT/status.tsv"
  echo "$name exit=$code elapsed=${elapsed}s"
}

run_check issue_regression "cd '$ROOT' && PYTHONPATH='$DJANGO' '$PY' -m unittest discover -s tests -p test_django_media_regression.py -v"
run_check forms_media "cd '$DJANGO' && '$PY' tests/runtests.py forms_tests.tests.test_media --noinput --parallel 1"
run_check admin_widgets "cd '$DJANGO' && '$PY' tests/runtests.py admin_widgets --noinput --parallel 1"

if awk -F '\t' 'NR>1 && $2 != 0 { bad=1 } END { exit !bad }' "$REPORT/status.tsv"; then
  echo "Verification has failures. See $REPORT/status.tsv" >&2
  exit 1
fi
echo "All executed verification commands passed. Review the patch before claiming task-level PASS."
