import argparse
import json
import subprocess
import sys
from pathlib import Path

from agent_cellphone.contracts.handoff import HandoffMessage
from agent_cellphone.contracts.message import CommandMessage
from agent_cellphone.runtime.event_log import EventLog
from agent_cellphone.runtime.handoff_router import HandoffRouter
from agent_cellphone.runtime.receive_loop import ReceiveLoop
from agent_cellphone.runtime.send_loop import SendLoop
from agent_cellphone.storage.artifact_store import ArtifactStore
from agent_cellphone.transport.cursor_adapter import CursorTransportAdapter


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def cmd_send(args: argparse.Namespace) -> int:
    loop = SendLoop(CursorTransportAdapter(), ArtifactStore(), EventLog())
    message = CommandMessage.model_validate(_load_json(Path(args.file)))
    result = loop.send(message, max_retries=args.max_retries)
    print(json.dumps(result, indent=2))
    return 1 if result["status"] == "failed" else 0


def cmd_receive(args: argparse.Namespace) -> int:
    loop = ReceiveLoop(ArtifactStore(), EventLog())
    try:
        response = loop.receive(args.run_id, args.task_id, to_actor=args.to_actor, timeout_seconds=args.timeout_seconds)
    except TimeoutError as exc:
        print(str(exc))
        return 1
    print(response.model_dump_json(indent=2))
    return 0


def cmd_handoff(args: argparse.Namespace) -> int:
    router = HandoffRouter(CursorTransportAdapter(), ArtifactStore(), EventLog())
    handoff_message = HandoffMessage.model_validate(_load_json(Path(args.file)))
    result = router.route(handoff_message)
    print(json.dumps(result, indent=2))
    return 1 if result["status"] == "failed" else 0


def cmd_events(args: argparse.Namespace) -> int:
    filters = {k: v for k, v in {"task_id": args.task_id, "agent_id": args.agent_id, "event_type": args.event_type}.items() if v}
    rows = EventLog().query(args.run_id, **filters)
    print(json.dumps(rows, indent=2))
    return 0


def cmd_smoke(_: argparse.Namespace) -> int:
    cmd = [sys.executable, "-m", "pytest", "-q", "tests/smoke"]
    return subprocess.run(cmd, check=False).returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent-cellphone")
    sub = parser.add_subparsers(dest="command", required=True)

    send = sub.add_parser("send")
    send.add_argument("--file", required=True)
    send.add_argument("--max-retries", type=int, default=2)
    send.set_defaults(func=cmd_send)

    receive = sub.add_parser("receive")
    receive.add_argument("--run-id", required=True)
    receive.add_argument("--task-id", required=True)
    receive.add_argument("--to-actor", default="human")
    receive.add_argument("--timeout-seconds", type=int, default=1)
    receive.set_defaults(func=cmd_receive)

    handoff = sub.add_parser("handoff")
    handoff.add_argument("--file", required=True)
    handoff.set_defaults(func=cmd_handoff)

    events = sub.add_parser("events")
    events.add_argument("--run-id", required=True)
    events.add_argument("--task-id")
    events.add_argument("--agent-id")
    events.add_argument("--event-type")
    events.set_defaults(func=cmd_events)

    smoke = sub.add_parser("smoke")
    smoke.set_defaults(func=cmd_smoke)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
