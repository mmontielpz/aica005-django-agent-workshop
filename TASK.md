# AICA005 — Django Media dependency ordering

**Workload:** SWE-bench Lite `django__django-11019` in `django/django` at `93e892bb645b16ebaf287beb5fe7f3ffe8d10408`.

**Issue:** [Django #30179](https://code.djangoproject.com/ticket/30179). When three or more widget `Media` definitions are combined, pairwise merging can invent an ordering constraint between independent assets. It may then warn about a conflict that does not exist and put `text-editor-extras.js` before its dependency `text-editor.js`.

**Goal:** Make the candidate change in `workspace/django/`. Preserve declared JavaScript and CSS dependencies, remove duplicates, handle real cycles honestly, and avoid related widget/admin regressions. No upstream solution patch is supplied; do not search for or apply one during an experiment.

**Starting state:** `bash scripts/preflight.sh --check` must confirm the pinned clean baseline. Both experiments use this same checkout and issue statement. Do not edit workshop contracts or regression tests to make a candidate appear successful.

**Acceptance:** Run `bash scripts/verify.sh A` or `B`, inspect failures and the patch, then `bash scripts/report.sh A` or `B`. A task-level PASS requires the issue regression, existing Django media tests, and adjacent admin widget checks to pass with reviewable evidence. If a check cannot run, report PARTIAL or BLOCKED.
