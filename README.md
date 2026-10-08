# AICA005 Django coding-agent workshop

This repository supports a controlled educational experiment. It contains only the Django Media workload, workshop contracts, and verification tools. It does not contain the Django solution patch or any observed A/B agent result.

## Workload and setup

- SWE-bench Lite task: `django__django-11019`
- [Original Django issue](https://code.djangoproject.com/ticket/30179)
- Historical Django base: `93e892bb645b16ebaf287beb5fe7f3ffe8d10408`
- Runtime: Python 3.7.17 in the devcontainer

Open this repository in GitHub Codespaces. The post-create command installs the pinned environment, runs baseline checks, and saves `reports/READINESS/summary.txt`. Wait for **LAB READY**. The issue regression should have three expected failures at baseline; unexpected failures mean the lab is not ready.

## Controlled A/B procedure

1. Record the environment, Copilot provider/model, Agent mode, account limits, and setup end time. Confirm Copilot access with a read-only request to summarize `TASK.md`.
2. Reset and confirm the baseline with `bash scripts/reset.sh` and `bash scripts/preflight.sh --check`.
3. Open [Experiment A](experiments/A-unstructured.md), submit its request in a fresh Agent session, and record agent start/end UTC timestamps. Review the patch.
4. Independently run `bash scripts/verify.sh A`, then `bash scripts/report.sh A`. Attach the Copilot transcript and any actual provider usage report in `reports/A/`; fill `reports/A/observations.json` from [the template](experiments/observations.template.json) and rerun the report command. Export A evidence outside the Codespace.
5. Reset and confirm the same baseline. Keep the model, Agent mode, account limits, and verification commands unchanged.
6. Open [Experiment B](experiments/B-resource-aware.md) in a fresh Agent session. Repeat the same evidence and verification procedure with run ID B, then export B evidence.
7. Run `python3 scripts/results.py compare`; export `reports/comparison.md` and `reports/comparison.json`.

Use the same task, acceptance criteria, runtime, dependencies, model, mode, available limits, and checks for both runs. Note the account limits in each run's `observations.json`, or write `NOT_AVAILABLE`. A is an unstructured work request. B changes the exploration and resource management policy. Keep setup time separate from agent execution time. Report tokens only from an attached provider record. Missing telemetry stays `NOT_AVAILABLE`; tool calls and elapsed time remain separate observations. A single A/B comparison is exploratory, not statistically conclusive.

`scripts/reset.sh` resets only `workspace/django` and leaves `reports/` intact. Export evidence before deleting the Codespace. The independent checks and patch review determine whether an outcome is supported; agent assertions alone do not.
