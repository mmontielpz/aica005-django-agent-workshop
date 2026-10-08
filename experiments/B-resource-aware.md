# Experiment B — resource-aware work request

After A's evidence is saved outside `workspace/django/`, run `bash scripts/reset.sh` and `bash scripts/preflight.sh --check`. Open a fresh Copilot Chat Agent session and submit:

> Read TASK.md, AGENT.md, VERIFY.md, and REPORT.md. Work on the same Django issue in workspace/django at the pinned baseline. First search the reported `Media` symbols and focused tests; inspect bounded source ranges before expanding. State an evidence checkpoint and a small plan. Reuse repository utilities when appropriate. Reserve time and context for the issue regression, existing media tests, and adjacent admin widgets. Expand context when a dependency or correctness risk justifies it. Make the smallest coherent patch, run the verification contract with run ID B, and report the patch, executed commands, resource evidence actually available, and remaining risks. Do not apply the upstream patch or claim success without executed evidence.

B changes the workflow policy, not the task or initial information. It is not guaranteed to use fewer resources or produce a better result. After the agent stops, the engineer reviews the diff, reruns `bash scripts/verify.sh B`, and generates `bash scripts/report.sh B`.
