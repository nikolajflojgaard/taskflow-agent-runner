# TaskFlow Agent Runner

Reusable workflow and small local state helper for durable agent work that waits, resumes, monitors, or spans multiple turns.

This skill sits above the core OpenClaw TaskFlow runtime. It keeps the authoring pattern clean: one owner flow, minimal persisted state, explicit waits, linked child work, and concise progress/final reports.

## What It Does

- Defines durable task state for waiting, resuming, monitoring, and finishing
- Separates owner context, child task context, wait metadata, and heartbeat/cron notes
- Covers CI/deploy waits, approvals, imports, releases, research, media generation, and scheduled jobs
- Provides stop, resume, escalation, and stale-state rules
- Produces concise progress and final reports

## Quick Start

Create a local flow packet:

```bash
python3 scripts/taskflow_agent_runner.py create "Watch deploy and report final status" --out /tmp/deploy-flow.json
```

Mark it waiting:

```bash
python3 scripts/taskflow_agent_runner.py wait /tmp/deploy-flow.json \
  --step await-ci \
  --kind ci \
  --reason "Waiting for GitHub Actions deploy run"
```

Resume and finish:

```bash
python3 scripts/taskflow_agent_runner.py resume /tmp/deploy-flow.json --step summarize
python3 scripts/taskflow_agent_runner.py finish /tmp/deploy-flow.json --summary "Deploy passed"
```

Render a Markdown status report:

```bash
python3 scripts/taskflow_agent_runner.py report /tmp/deploy-flow.json
```

The CLI is a local scaffold and state helper. Production OpenClaw controllers should use `api.runtime.tasks.flow`.

## Skill Contents

- `SKILL.md` - durable runner workflow
- `scripts/taskflow_agent_runner.py` - local state helper and report renderer
- `templates/` - state, progress, final, and child task templates
- `references/openclaw-taskflow.md` - runtime call pattern and design boundaries
- `examples/ci-deploy-flow.json` - example wait/resume flow
- `docs/` - generated documentation

## Safety

Do not use background state as an excuse to hide uncertainty. If a flow waits on approval, secrets, failed CI, or external systems, preserve the state and report the exact blocker.
