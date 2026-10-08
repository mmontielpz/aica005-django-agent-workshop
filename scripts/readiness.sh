#!/usr/bin/env bash
set -u -o pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DJANGO="$ROOT/workspace/django"
BASE=93e892bb645b16ebaf287beb5fe7f3ffe8d10408
SUMMARY="$ROOT/reports/READINESS/summary.txt"
mkdir -p "$(dirname "$SUMMARY")"

mode="${1:---check}"
if [[ "$mode" != --setup && "$mode" != --check ]]; then
  echo "Usage: bash scripts/readiness.sh [--setup|--check]" >&2
  exit 2
fi

if ! bash "$ROOT/scripts/preflight.sh" "$mode"; then
  {
    echo "LAB NOT READY"
    echo "Environment readiness: preflight failed; no workspace reset was attempted."
    echo "Django commit: $(git -C "$DJANGO" rev-parse HEAD 2>/dev/null || echo UNAVAILABLE)"
    echo "Baseline regression: NOT RUN"
    echo "Existing tests: NOT RUN"
    echo "Next participant action: inspect the preflight error; save existing work before any manual reset."
  } | tee "$SUMMARY"
  exit 1
fi

bash "$ROOT/scripts/verify.sh" READINESS
verify_code=$?
status="$ROOT/reports/READINESS/status.tsv"
log="$ROOT/reports/READINESS/issue_regression.log"
code_for() { awk -F '\t' -v name="$1" '$1 == name { print $2 }' "$status" 2>/dev/null; }
issue_code="$(code_for issue_regression)"
forms_code="$(code_for forms_media)"
admin_code="$(code_for admin_widgets)"

expected_regression=false
if [[ "$issue_code" == 1 && -f "$log" ]] \
  && grep -Fq 'Ran 4 tests' "$log" \
  && grep -Fq 'FAILED (failures=3)' "$log" \
  && grep -Fq 'test_css_dependency_and_deduplication (test_django_media_regression.MediaDependencyRegressionTests) ... FAIL' "$log" \
  && grep -Fq 'test_duplicate_in_single_definition (test_django_media_regression.MediaDependencyRegressionTests) ... FAIL' "$log" \
  && grep -Fq 'test_three_way_js_dependency (test_django_media_regression.MediaDependencyRegressionTests) ... FAIL' "$log" \
  && grep -Fq 'test_real_cycle_warns_without_losing_assets (test_django_media_regression.MediaDependencyRegressionTests) ... ok' "$log"; then
  expected_regression=true
fi

if [[ "$expected_regression" == true && "$forms_code" == 0 && "$admin_code" == 0 && "$verify_code" == 1 ]]; then
  {
    echo "LAB READY"
    echo "Environment readiness: Python and pinned Django checkout passed preflight."
    echo "Django commit: $BASE"
    echo "Baseline regression: 3 expected failures; cycle case passed. The issue remains unfixed."
    echo "Existing tests: forms media and admin widgets passed."
    echo "Next participant action: read TASK.md, open Copilot Agent, and use experiments/A-unstructured.md."
  } | tee "$SUMMARY"
  exit 0
fi

{
  echo "LAB NOT READY"
  echo "Environment readiness: baseline check differs from the qualified historical baseline."
  echo "Django commit: $(git -C "$DJANGO" rev-parse HEAD 2>/dev/null || echo UNAVAILABLE)"
  echo "Baseline regression: unexpected result (exit ${issue_code:-UNAVAILABLE})."
  echo "Existing tests: forms media exit ${forms_code:-UNAVAILABLE}; admin widgets exit ${admin_code:-UNAVAILABLE}."
  echo "Next participant action: inspect reports/READINESS/*.log and status.tsv; do not start A or B yet."
} | tee "$SUMMARY"
exit 1
