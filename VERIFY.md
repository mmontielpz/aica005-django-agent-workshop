# Verification contract

Run from the lab repository root. `bash scripts/verify.sh A` or `B` writes genuine command logs and exit codes under ignored `reports/<run>/`. It does not apply a fix.

The script runs:

1. A source-backed regression probe for the issue's three-way JS merge, parallel CSS behavior, deduplication, and real cycle warning.
2. Django's existing `forms_tests.tests.test_media` suite.
3. Django's existing `admin_widgets` suite for adjacent widget behavior.

The regression probe is expected to expose the historical bug on the untouched baseline. A failing baseline is evidence that the check detects the defect, not a failed setup. After a candidate patch, require all commands to pass and review `git diff` before claiming task-level PASS. If dependencies or environment prevent a command from running, preserve its log and report the limitation.
