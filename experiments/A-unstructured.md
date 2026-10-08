# Experiment A — normal work request

Open Copilot Chat in Agent mode and submit the fixed request below. The agent runs the commands; approve tool actions when prompted.

> Read TASK.md, AGENT.md, VERIFY.md, and REPORT.md. Confirm LAB READY, then run `bash scripts/reset.sh` and `bash scripts/preflight.sh --check` before editing. Work on the Django issue in workspace/django at the pinned baseline. Investigate the Media ordering defect and make a focused correction with appropriate tests. Run `bash scripts/verify.sh A`, then run `bash scripts/report.sh A` even if a check fails. Record only directly observed metadata in `reports/A/observations.json`; attach a transcript or provider record only if genuinely available, and otherwise leave those fields NOT_AVAILABLE or NOT_OBSERVED. Report the patch, command results, remaining risks, and `reports/A/evidence.zip` location. Do not apply the upstream patch or claim success without executed evidence.
>
> Stop before modifying Django if reset or preflight fails; report the failure rather than continuing from an unverified checkout. Confirm preflight reports the clean pinned baseline.
>
> Use a five-minute target from the end of preflight for investigation, implementation, verification, and reporting. This is a policy target, not an enforced timeout. Record UTC start and end times only if reliably observed; keep setup time separate. At the limit, stop investigating and editing; attempt verification and evidence packaging where feasible, and report incomplete work accurately.

This is a normal engineering request. It has the same task, checkout, contracts, and tools as B; it does not prescribe an exploration budget. After the agent stops, the engineer reviews the diff and ZIP, exports the evidence outside the Codespace, and may independently rerun the same verification. Record observed time, interventions, and any provider-reported usage separately.
