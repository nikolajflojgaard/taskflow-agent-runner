---
name: taskflow-agent-runner
description: Run durable agent tasks with OpenClaw TaskFlow patterns; use for background jobs that wait, resume, monitor CI/deploys, handle approvals, coordinate child tasks, survive context loss, and produce progress/final reports without stale heartbeat state.
---

# TaskFlow Agent Runner

Use this skill when agent work needs to outlive one prompt, wait for an external event, monitor a long-running job, or resume later without relying on stale chat context.

This skill is the operating pattern around OpenClaw TaskFlow. The core runtime owns flow identity, state, waits, linked child tasks, and revision-safe mutations. The agent runner owns the human workflow: what state to keep, when to wait, how to resume, and how to report.

## Use It For

- CI/deploy monitoring
- release watches
- imports that finish later
- research jobs with checkpoints
- media generation jobs
- approval waits
- scheduled or cron-triggered work
- child-agent orchestration that needs one durable parent

Do not use it for small tasks that can finish in the current turn.

## Runtime Boundary

Use core OpenClaw TaskFlow when available:

- canonical entrypoint: `api.runtime.tasks.flow`
- bind from tool context with `api.runtime.tasks.flow.fromToolContext(ctx)`
- create managed flows with `createManaged(...)`
- link child work with `runTask(...)`
- wait with `setWaiting(...)`
- resume with `resume(...)`
- finish or fail with `finish(...)` / `fail(...)`
- cancel with `requestCancel(...)` or `cancel(...)`

Keep branching and business logic above the runtime. TaskFlow is the durable state and linkage layer, not a domain-specific language.

## Runner Workflow

1. **Decide if the task deserves a flow**
   Use a flow when at least one is true:
   - work waits on a human, CI, deploy, API job, generated media, or scheduled time
   - child tasks must report back to one owner
   - state must survive context loss
   - a future heartbeat or cron turn needs to resume cleanly

2. **Create minimal owner state**
   Store only what is needed to resume:
   - goal
   - current step
   - owner/requester context
   - child task summaries
   - wait metadata
   - artifact links
   - approval status
   - validation status

3. **Separate state types**
   - `ownerContext`: what the original requester needs and where final output goes
   - `stateJson`: durable job state and artifacts
   - `waitJson`: external wait condition
   - `childTasks`: linked child jobs, status, and handoff
   - `heartbeatNotes`: tiny resume hints only, never stale task plans

4. **Launch child tasks deliberately**
   - Use `runTask(...)` for linked child tasks when using the OpenClaw runtime.
   - Give child tasks narrow context and stop conditions.
   - Do not let detached children become the source of truth.

5. **Set waiting honestly**
   Use waiting for:
   - human approval
   - CI/deploy completion
   - external async jobs
   - scheduled resume time
   - dependency on another task

   Include a human-readable reason and structured `waitJson`.

6. **Resume only with evidence**
   On resume:
   - inspect wait condition
   - refresh child task status
   - carry forward the latest runtime revision
   - update state with new evidence
   - finish, fail, wait again, or escalate

7. **Escalate instead of looping**
   Escalate when:
   - approval is needed
   - secrets or credentials are missing
   - CI/deploy fails
   - the same blocker repeats
   - state is stale or contradictory
   - a child task returns low confidence on high-risk work

8. **Report cleanly**
   Progress reports should include:
   - current step
   - waiting reason, if any
   - child task status
   - artifacts
   - next resume condition

   Final reports should include:
   - outcome
   - validation
   - commits, links, or artifacts
   - unresolved risks
   - whether the flow is finished, failed, cancelled, or still waiting

## Local State Helper

Use the bundled script to create and inspect local flow packets while designing a workflow:

```bash
python3 scripts/taskflow_agent_runner.py create "<goal>" --out flow.json
python3 scripts/taskflow_agent_runner.py wait flow.json --step await-ci --kind ci --reason "Waiting for deploy"
python3 scripts/taskflow_agent_runner.py resume flow.json --step summarize
python3 scripts/taskflow_agent_runner.py finish flow.json --summary "Done"
python3 scripts/taskflow_agent_runner.py report flow.json
```

This helper does not call OpenClaw runtime APIs. It is for local planning, examples, tests, and handoff packets.

## Heartbeat And Cron Rules

- Use heartbeat for broad, low-urgency checks that can drift.
- Use cron for precise timing or isolated background work.
- Keep heartbeat state tiny.
- Do not duplicate cron jobs and TaskFlow waits for the same condition.
- Clear or finish stale waits instead of carrying them forever.

## Approval Waits

When waiting for approval:

- record who can approve
- record what action is blocked
- record safe alternatives
- do not perform the external/public action early
- resume only when approval evidence is available

## Stale State Rules

Treat a flow as stale when:

- wait condition no longer exists
- child task is gone or uninspectable
- target repo/branch changed underneath the flow
- approval expired
- heartbeat notes contradict runtime state

On stale state, report and rebuild from source evidence instead of pretending continuity is perfect.

## References

Read `references/openclaw-taskflow.md` when implementing a real OpenClaw controller or mapping this workflow to runtime calls.
