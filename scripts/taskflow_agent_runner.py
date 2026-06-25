#!/usr/bin/env python3
"""Create and update local TaskFlow runner packets."""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:48] or "taskflow"


def now_ms() -> int:
    return int(time.time() * 1000)


def read_flow(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"{path}: root must be a JSON object")
    return value


def write_flow(path: Path, flow: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(flow, indent=2) + "\n", encoding="utf-8")


def bump(flow: dict[str, Any]) -> None:
    flow["revision"] = int(flow.get("revision", 0)) + 1
    flow["updatedAt"] = now_ms()


def command_create(args: argparse.Namespace) -> int:
    created_at = now_ms()
    flow = {
        "flowId": args.flow_id or f"flow-{slugify(args.goal)}",
        "goal": args.goal,
        "status": "running",
        "currentStep": args.step,
        "revision": 1,
        "createdAt": created_at,
        "updatedAt": created_at,
        "ownerContext": {
            "requester": args.requester or "",
            "delivery": args.delivery or "",
            "finalReportTarget": args.final_report_target or "",
        },
        "stateJson": {
            "artifacts": [],
            "validation": [],
            "notes": [],
        },
        "waitJson": None,
        "childTasks": [],
        "heartbeatNotes": [],
    }
    write_flow(args.out, flow)
    print(f"Created {args.out}")
    return 0


def command_wait(args: argparse.Namespace) -> int:
    flow = read_flow(args.flow)
    flow["status"] = "waiting"
    flow["currentStep"] = args.step
    flow["waitJson"] = {
        "kind": args.kind,
        "reason": args.reason,
        "step": args.step,
        "createdAt": now_ms(),
    }
    if args.resume_after:
        flow["waitJson"]["resumeAfter"] = args.resume_after
    bump(flow)
    write_flow(args.flow, flow)
    print(f"{args.flow}: waiting on {args.kind}")
    return 0


def command_resume(args: argparse.Namespace) -> int:
    flow = read_flow(args.flow)
    flow["status"] = "running"
    flow["currentStep"] = args.step
    flow["waitJson"] = None
    note = args.evidence
    if note:
        flow.setdefault("stateJson", {}).setdefault("notes", []).append(note)
    bump(flow)
    write_flow(args.flow, flow)
    print(f"{args.flow}: resumed at {args.step}")
    return 0


def command_child(args: argparse.Namespace) -> int:
    flow = read_flow(args.flow)
    child = {
        "runId": args.run_id,
        "runtime": args.runtime,
        "task": args.task,
        "status": args.status,
        "startedAt": now_ms(),
        "lastEventAt": now_ms(),
        "handoff": "",
    }
    flow.setdefault("childTasks", []).append(child)
    bump(flow)
    write_flow(args.flow, flow)
    print(f"{args.flow}: added child {args.run_id}")
    return 0


def command_child_status(args: argparse.Namespace) -> int:
    flow = read_flow(args.flow)
    child_tasks = flow.setdefault("childTasks", [])
    for task in child_tasks:
        if task.get("runId") == args.run_id:
            task["status"] = args.status
            task["lastEventAt"] = now_ms()
            if args.handoff:
                task["handoff"] = args.handoff
            bump(flow)
            write_flow(args.flow, flow)
            print(f"{args.flow}: updated child {args.run_id}")
            return 0
    raise SystemExit(f"{args.flow}: child not found: {args.run_id}")


def command_artifact(args: argparse.Namespace) -> int:
    flow = read_flow(args.flow)
    flow.setdefault("stateJson", {}).setdefault("artifacts", []).append(args.value)
    bump(flow)
    write_flow(args.flow, flow)
    print(f"{args.flow}: added artifact")
    return 0


def command_finish(args: argparse.Namespace) -> int:
    flow = read_flow(args.flow)
    flow["status"] = "finished"
    flow["currentStep"] = "finished"
    flow["waitJson"] = None
    flow.setdefault("stateJson", {})["summary"] = args.summary
    bump(flow)
    write_flow(args.flow, flow)
    print(f"{args.flow}: finished")
    return 0


def command_fail(args: argparse.Namespace) -> int:
    flow = read_flow(args.flow)
    flow["status"] = "failed"
    flow["currentStep"] = "failed"
    flow.setdefault("stateJson", {})["failure"] = args.reason
    bump(flow)
    write_flow(args.flow, flow)
    print(f"{args.flow}: failed")
    return 0


def command_report(args: argparse.Namespace) -> int:
    flow = read_flow(args.flow)
    report = render_report(flow)
    if args.out:
        args.out.write_text(report, encoding="utf-8")
        print(f"Wrote {args.out}")
    else:
        print(report)
    return 0


def render_report(flow: dict[str, Any]) -> str:
    state = flow.get("stateJson") or {}
    wait = flow.get("waitJson")
    child_tasks = flow.get("childTasks") or []
    artifacts = state.get("artifacts") or []
    validation = state.get("validation") or []
    lines = [
        "# TaskFlow Runner Report",
        "",
        "## Goal",
        "",
        str(flow.get("goal", "")),
        "",
        "## Status",
        "",
        f"- Status: {flow.get('status')}",
        f"- Current step: {flow.get('currentStep')}",
        f"- Revision: {flow.get('revision')}",
        "",
        "## Waiting",
        "",
    ]
    if wait:
        lines.extend(
            [
                f"- Kind: {wait.get('kind')}",
                f"- Reason: {wait.get('reason')}",
                f"- Step: {wait.get('step')}",
            ]
        )
    else:
        lines.append("- None")

    lines.extend(["", "## Child Tasks", ""])
    if child_tasks:
        for task in child_tasks:
            lines.append(
                f"- {task.get('runId')}: {task.get('status')} - {task.get('task')}"
            )
    else:
        lines.append("- None")

    lines.extend(["", "## Artifacts", ""])
    lines.extend(f"- {item}" for item in artifacts) if artifacts else lines.append("- None")

    lines.extend(["", "## Validation", ""])
    lines.extend(f"- {item}" for item in validation) if validation else lines.append("- None")

    if state.get("summary"):
        lines.extend(["", "## Summary", "", str(state["summary"])])
    if state.get("failure"):
        lines.extend(["", "## Failure", "", str(state["failure"])])
    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create", help="create a local flow packet")
    create.add_argument("goal")
    create.add_argument("--out", type=Path, required=True)
    create.add_argument("--flow-id")
    create.add_argument("--step", default="start")
    create.add_argument("--requester")
    create.add_argument("--delivery")
    create.add_argument("--final-report-target")
    create.set_defaults(func=command_create)

    wait = sub.add_parser("wait", help="mark a flow waiting")
    wait.add_argument("flow", type=Path)
    wait.add_argument("--step", required=True)
    wait.add_argument("--kind", required=True)
    wait.add_argument("--reason", required=True)
    wait.add_argument("--resume-after")
    wait.set_defaults(func=command_wait)

    resume = sub.add_parser("resume", help="resume a waiting flow")
    resume.add_argument("flow", type=Path)
    resume.add_argument("--step", required=True)
    resume.add_argument("--evidence")
    resume.set_defaults(func=command_resume)

    child = sub.add_parser("child", help="add a child task record")
    child.add_argument("flow", type=Path)
    child.add_argument("--run-id", required=True)
    child.add_argument("--runtime", default="subagent")
    child.add_argument("--task", required=True)
    child.add_argument("--status", default="running")
    child.set_defaults(func=command_child)

    child_status = sub.add_parser("child-status", help="update a child task")
    child_status.add_argument("flow", type=Path)
    child_status.add_argument("--run-id", required=True)
    child_status.add_argument("--status", required=True)
    child_status.add_argument("--handoff")
    child_status.set_defaults(func=command_child_status)

    artifact = sub.add_parser("artifact", help="add an artifact link or path")
    artifact.add_argument("flow", type=Path)
    artifact.add_argument("value")
    artifact.set_defaults(func=command_artifact)

    finish = sub.add_parser("finish", help="finish a flow")
    finish.add_argument("flow", type=Path)
    finish.add_argument("--summary", required=True)
    finish.set_defaults(func=command_finish)

    fail = sub.add_parser("fail", help="fail a flow")
    fail.add_argument("flow", type=Path)
    fail.add_argument("--reason", required=True)
    fail.set_defaults(func=command_fail)

    report = sub.add_parser("report", help="render Markdown flow report")
    report.add_argument("flow", type=Path)
    report.add_argument("--out", type=Path)
    report.set_defaults(func=command_report)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
