# Participant Quick Start
**AI Coding Agents: Resource-Aware Engineering · 60 minutes**

Same task, baseline, model, runtime and verification; different workflow. Run commands from the lab repository root. Use your own Codespace.

## 1. Prepare
Sign in to GitHub with Codespaces access, remaining compute/storage allowance, and Copilot Chat **Agent** access. [Launch the lab](https://codespaces.new/mmontielpz/aica005-django-agent-workshop/tree/main); choose **2 cores** if available. Public repository access does not grant Copilot access. Free allowances are limited; check your [Codespaces allowance](https://docs.github.com/en/codespaces/troubleshooting/troubleshooting-included-usage) and [Copilot plan](https://docs.github.com/en/copilot/get-started/plans). Record the selected model and account limits. If a fixed model is unavailable, record that limitation; do not claim a same-model comparison.

## 2. Check
Wait for **LAB READY**, then:
```bash
bash scripts/preflight.sh --check
```
This checks a clean Django baseline at `93e892bb645b16ebaf287beb5fe7f3ffe8d10408`. Baseline issue failures are expected; unexpected readiness failures require investigation before starting.

Select Copilot Chat **Agent** mode and send this read-only request:
> Read TASK.md and summarize the task and acceptance criteria. Do not edit files or run commands.

Confirm a response, record the model, then start a **fresh chat** for A.

## 3. Experiment A
```bash
bash scripts/reset.sh
bash scripts/preflight.sh --check
```
Open the [fixed A request](https://github.com/mmontielpz/aica005-django-agent-workshop/blob/main/experiments/A-unstructured.md) and paste its complete request into Agent mode. Observe for **five minutes**, stopping earlier if complete. Record UTC start/end times, permissions and assistance. Do not coach the agent.

Independently inspect and verify, even if the agent already ran tests:
```bash
git -C workspace/django diff
git -C workspace/django status --short
bash scripts/verify.sh A
bash scripts/report.sh A
```
If verification fails, retain its logs and still run the report command. Passing checks require patch review; report incomplete outcomes honestly.

**Save evidence before resetting.** If missing, copy `experiments/observations.template.json` to `reports/A/observations.json`. Fill the actual provider/model/mode, limits, UTC timestamps, execution status and outcome. Save the real conversation in `reports/A/` and set `transcript_ref` to its filename. Record interventions and patch review in that directory. Keep unavailable numeric metrics `null`; token `source_type` stays `NOT_AVAILABLE` without an attached provider report. Then:
```bash
bash scripts/report.sh A
tar --exclude=.git -czf reports/A/candidate.tar.gz -C workspace/django .
tar -czf /tmp/AICA005-A-evidence.tar.gz reports/A
```
In VS Code, use **File → Add Folder to Workspace → /tmp**, then right-click `AICA005-A-evidence.tar.gz` in Explorer and choose **Download** before B. It contains reports and candidate files, including untracked additions.

## 4. Experiment B
After exporting A:
```bash
bash scripts/reset.sh
bash scripts/preflight.sh --check
```
Reset discards changes and untracked files in `workspace/django/`; `reports/` remains. Start a fresh chat, keep the **same model and conditions**, and paste the [fixed B request](https://github.com/mmontielpz/aica005-django-agent-workshop/blob/main/experiments/B-resource-aware.md). Use the same five-minute window without hints from A.
```bash
git -C workspace/django diff
git -C workspace/django status --short
bash scripts/verify.sh B
bash scripts/report.sh B
```
Repeat A's evidence procedure in `reports/B/`, setting `run_id` to **B** in its observations file. Attach B's conversation and actual measurements, then:
```bash
bash scripts/report.sh B
tar --exclude=.git -czf reports/B/candidate.tar.gz -C workspace/django .
tar -czf /tmp/AICA005-B-evidence.tar.gz reports/B
```
Download B's archive. Never reuse A's patch or chat.

## 5. Compare
```bash
python3 scripts/results.py compare
tar -czf /tmp/AICA005-all-evidence.tar.gz reports
```
Read `reports/comparison.md` and `reports/comparison.json`; download the final archive. Compare verification, reviewed patches, agent duration and observable tool activity. Missing token telemetry is **NOT_AVAILABLE**; never infer tokens from time or tool calls. A generated percentage is not a correctness verdict: interpret savings only after equivalent verified outcomes and comparable provider records. One A/B pair is exploratory; B may fail or consume more.

## 6. Cleanup
After confirming your downloaded evidence, open [Your codespaces](https://github.com/codespaces), find **this lab's Codespace**, and use **… → Stop codespace**. Closing the tab does not stop it. Stopping ends compute usage, but storage continues consuming quota or incurring charges. When no longer needed, use **… → Delete** after exporting evidence; deletion does not undo accrued usage. See [stopping](https://docs.github.com/en/codespaces/developing-in-a-codespace/stopping-and-starting-a-codespace) and [deleting](https://docs.github.com/en/codespaces/developing-in-a-codespace/deleting-a-codespace).

Detailed contracts and commands: [README](https://github.com/mmontielpz/aica005-django-agent-workshop/blob/main/README.md).
