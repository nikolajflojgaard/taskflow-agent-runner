# OpenClaw TaskFlow Runtime Pattern

Use this reference when mapping the runner workflow to real OpenClaw runtime calls.

## Canonical Runtime

- `api.runtime.tasks.flow`
- `api.runtime.tasks.flow.fromToolContext(ctx)`
- `api.runtime.tasks.flow.bindSession({ sessionKey, requesterOrigin })`

## Managed Flow Lifecycle

1. `createManaged(...)`
2. `runTask(...)`
3. `setWaiting(...)`
4. `resume(...)`
5. `finish(...)` or `fail(...)`
6. `requestCancel(...)` or `cancel(...)`

## Revision Rule

Every mutating method after creation is revision-checked. Carry forward the latest `flow.revision` after every successful mutation.

## State Rule

Treat `stateJson` as the persisted state bag. There is no separate append-output API. Store only what is needed to resume.

## Child Task Rule

Use `runTask(...)` when linked child work should belong to the parent flow. Do not manually create detached tasks when parent orchestration matters.

## Waiting Shape

Use `setWaiting(...)` with:

- `currentStep`
- updated `stateJson`
- structured `waitJson`
- human-readable blocked/wait reason when available

Example wait JSON:

```json
{
  "kind": "ci",
  "provider": "github-actions",
  "runId": "28108446746",
  "repo": "owner/repo"
}
```

## Keep Logic Above Runtime

The runtime should not own business branching. Keep decisions in the controller or agent workflow:

- approval needed -> wait
- CI passed -> summarize and finish
- CI failed -> collect logs and escalate
- child blocked -> wait or fail depending on severity
