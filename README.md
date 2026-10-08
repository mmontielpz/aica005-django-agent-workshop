# AICA005 Django coding-agent workshop

This repository supports a controlled educational experiment. It contains only the Django Media workload, workshop contracts, and verification tools. It does not contain the Django solution patch or any observed A/B agent result.

## Workload and setup

- SWE-bench Lite task: `django__django-11019`
- [Original Django issue](https://code.djangoproject.com/ticket/30179)
- Historical Django base: `93e892bb645b16ebaf287beb5fe7f3ffe8d10408`
- Runtime: Python 3.7.17 in the devcontainer

Open this repository in GitHub Codespaces. The post-create command installs the pinned environment, runs baseline checks, and saves `reports/READINESS/summary.txt`. Wait for **LAB READY**. The issue regression should have three expected failures at baseline; unexpected failures mean the lab is not ready.

## Controlled A/B procedure

1. Open Copilot Chat in Agent mode. Confirm access with a read-only request to summarize `TASK.md`; note the provider/model and available account limits.
2. Submit the fixed [Experiment A request](experiments/A-unstructured.md) in a fresh Agent session. Approve tool actions as needed. The agent runs reset, preflight, verification, and reporting. Review `reports/A/evidence.zip` and export it **outside the Codespace** before B.
3. Submit the fixed [Experiment B request](experiments/B-resource-aware.md) in a fresh Agent session with the same model and Agent mode. The agent resets the Django checkout, runs the same checks, packages `reports/B/evidence.zip`, and runs the comparison.
4. Review `reports/B/evidence.zip`, `reports/comparison.md`, and `reports/comparison.json`; export them outside the Codespace. Check each patch and the actual command logs before interpreting the comparison.

The normal participant path is **Prompt A → Review evidence → Prompt B → Review comparison**. The participant need not type shell commands. The commands remain available for independent review: `bash scripts/preflight.sh --check`, `bash scripts/verify.sh A|B`, `bash scripts/report.sh A|B`, and `python3 scripts/results.py compare`. If Copilot cannot execute a command, record that limit and run the same script manually rather than inferring success.

Use the same task, acceptance criteria, runtime, dependencies, model, mode, available limits, and checks for both runs. Note the account limits in each run's `observations.json`, or write `NOT_AVAILABLE`. A is an unstructured work request. B changes the exploration and resource management policy. Keep setup time separate from agent execution time. Report tokens only from an attached provider record. Missing telemetry stays `NOT_AVAILABLE`; tool calls and elapsed time remain separate observations. A single A/B comparison is exploratory, not statistically conclusive.

`scripts/reset.sh` resets only `workspace/django` and leaves `reports/` intact. Export evidence before deleting the Codespace. The independent checks and patch review determine whether an outcome is supported; agent assertions alone do not.
