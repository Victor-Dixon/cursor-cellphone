import pytest

from agent_cellphone.contracts.message import CommandMessage
from agent_cellphone.runtime.event_log import EventLog
from agent_cellphone.runtime.send_loop import SendLoop
from agent_cellphone.storage.artifact_store import ArtifactStore
from agent_cellphone.transport.cursor_adapter import CursorTransportAdapter


def test_failure_visibility(tmp_path):
    store = ArtifactStore(base_dir=tmp_path)
    events = EventLog(base_dir=tmp_path)
    send_loop = SendLoop(CursorTransportAdapter(known_agents={"agent-1"}), store, events)

    command = CommandMessage(
        message_id="msg-f1",
        run_id="run-f",
        task_id="task-f",
        from_actor="human",
        to_agent="agent-9",
        message_type="command",
        payload={"instruction": "do thing"},
        priority="normal",
        created_at="2026-03-28T15:00:00Z",
        timeout_seconds=10,
        requires_response=False,
        correlation_id="corr-f",
    )
    result = send_loop.send(command)
    assert result["status"] == "failed"

    rows = events.query("run-f")
    assert any(r["event_type"] == "message_delivery_failed" for r in rows)
    assert any(r["event_type"] == "transport_error" for r in rows)
    assert store.exists("run-f", "commands", "msg-f1")


def test_receive_timeout_emits_event(tmp_path):
    store = ArtifactStore(base_dir=tmp_path)
    events = EventLog(base_dir=tmp_path)

    from agent_cellphone.runtime.receive_loop import ReceiveLoop

    loop = ReceiveLoop(store, events)
    with pytest.raises(TimeoutError):
        loop.receive("run-timeout", "task-timeout", to_actor="human", timeout_seconds=0)
    assert any(r["event_type"] == "timeout_reached" for r in events.query("run-timeout"))
