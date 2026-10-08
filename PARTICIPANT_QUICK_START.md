# Participant Quick Start

**AI Coding Agents: Resource-Aware Engineering · 60-minute workshop**

Your path is **Prompt A → Evidence A → Prompt B → Evidence B → Benchmark → Engineering Decision**. Copilot runs the scripts; you approve actions, review evidence, and decide what the results support. No shell commands are required in the normal flow.

Start **each** experiment in a fresh Copilot Agent chat with no inherited file attachments or prior experiment context. A fresh chat separates agent context; Copilot's reset and preflight isolate the Django code at the clean pinned baseline. Stop before editing if either check fails. The reset leaves `reports/` intact; export the previous run's evidence before continuing.

1. [Launch the public Codespaces lab](https://codespaces.new/mmontielpz/aica005-django-agent-workshop/tree/main). Wait for **LAB READY**. Open Copilot Chat in **Agent** mode. Confirm access with a read-only request to summarize `TASK.md`. Note the model and available account limits. Public repository access alone does not grant Copilot access.
2. Start a fresh Agent chat without inherited attachments and paste the complete [Experiment A request](experiments/A-unstructured.md). Copilot resets the pinned Django baseline, runs preflight, investigates, edits, verifies, and packages `reports/A/evidence.zip`. Approve tool actions when required. Review and **download A's ZIP outside the Codespace before B**.
3. Start a **new Agent chat** for [Experiment B](experiments/B-resource-aware.md). Remove inherited A file attachments and prior chat context. Keep the same model, mode, runtime, task, baseline, and verification where available. Paste the complete B request. Copilot resets Django, performs the resource-aware workflow, packages `reports/B/evidence.zip`, and runs the comparison.
4. Review and download `reports/B/evidence.zip`, `reports/comparison.md`, and `reports/comparison.json`. Inspect both patches and test logs. Discuss which observations are verified and which claims remain inconclusive. Verification equivalence is limited to the required checks; it does not prove equal solutions or efficiency.
5. After confirming your downloads, [stop and delete this Codespace](https://github.com/codespaces) when no longer needed. Deletion is permanent, so export evidence first. Closing the browser tab alone does not stop compute usage.

Use a **3–5-minute workshop window per experiment**, with the same **five-minute target** for A and B. Timing starts after preflight and includes investigation, implementation, verification, and reporting. The prompts express a policy target; they do not enforce a process timeout. At the limit, stop further exploration and editing, then attempt verification and evidence packaging where feasible. Record incomplete work honestly.

Free-tier limits, model routing, and provider telemetry may vary. If the same model is unavailable, record that limitation. Tokens and cost remain `NOT_AVAILABLE` without actual comparable provider evidence; never estimate tokens from time or tool calls. One A/B pair is exploratory.

The [README](README.md), [verification contract](VERIFY.md), and [report contract](REPORT.md) describe the scripts for independent review. If Copilot cannot run them, note that limitation and use the same scripts manually; do not infer success from the prompt alone.
