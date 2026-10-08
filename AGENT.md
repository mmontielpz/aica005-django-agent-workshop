# Agent working agreement

Make source edits only in `workspace/django/` after the engineer chooses experiment A or B. Run the lab's setup, verification, and reporting scripts from the repository root. The engineer owns the final decision and reviews the script-generated verification evidence. Read `TASK.md` and `VERIFY.md` before editing.

Use repository evidence to localize the cause. Make the smallest coherent patch and add or adjust Django tests when needed. Do not copy the upstream solution patch. Do not modify this lab's `scripts/`, contracts, or `tests/` to bypass a failing check. Do not claim success from a narrow passing test or from an unexecuted command.

Record commands, observations, changed files, remaining risks, and any resource metrics actually exposed by Copilot. Token totals, provider quotas, and cost are **UNAVAILABLE** unless a provider reports them for this run. Do not estimate them from tool output or time.
