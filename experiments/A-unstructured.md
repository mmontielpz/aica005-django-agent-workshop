# Experiment A — normal work request

Start with `bash scripts/reset.sh`, then `bash scripts/preflight.sh --check`. Open Copilot Chat in Agent mode and submit:

> Read TASK.md, AGENT.md, VERIFY.md, and REPORT.md. Work on the Django issue in workspace/django at the pinned baseline. Investigate the Media ordering defect, make a focused correction with appropriate tests, run the verification contract with run ID A, and report the patch, command results, and remaining risks. Do not apply the upstream patch or claim success without executed evidence.

This is a normal engineering request. It has the same task, checkout, contracts, and tools as B; it does not prescribe an exploration budget. After the agent stops, the engineer reviews the diff, reruns `bash scripts/verify.sh A`, and generates `bash scripts/report.sh A`. Record observed time, interventions, and any provider-reported usage separately.
