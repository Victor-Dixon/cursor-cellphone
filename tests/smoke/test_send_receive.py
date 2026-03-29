from agent_cellphone.contracts.message import CommandMessage
from agent_cellphone.contracts.response import ResponseMessage
from agent_cellphone.runtime.event_log import EventLog
from agent_cellphone.runtime.receive_loop import ReceiveLoop
from agent_cellphone.runtime.send_loop import SendLoop
from agent_cellphone.storage.artifact_store import ArtifactStore
from agent_cellphone.transport.cursor_adapter import CursorTransportAdapter


def test_send_receive_happy_path(tmp_path):
    store = ArtifactStore(base_dir=tmp_path)
    events = EventLog(base_dir=tmp_path)
    send_loop = SendLoop(CursorTransportAdapter(), store, events)
    receive_loop = ReceiveLoop(store, events)

    command = CommandMessage(
        message_id="msg-1",
        run_id="run-1",
        task_id="task-1",
        from_actor="human",
        to_agent="agent-3",
        message_type="command",
        payload={"instruction": "do thing"},
        priority="normal",
        created_at="2026-03-28T15:00:00Z",
        timeout_seconds=10,
        requires_response=True,
        correlation_id="corr-1",
    )
    result = send_loop.send(command)
    assert result["status"] == "awaiting_response"

    response = ResponseMessage(
        message_id="msg-2",
        run_id="run-1",
        task_id="task-1",
        from_agent="agent-3",
        to_actor="human",
        status="responded",
        summary=["done"],
        artifacts=[],
        errors=[],
        created_at="2026-03-28T15:01:00Z",
        correlation_id="corr-1",
    )
    store.write_json("run-1", "responses", "task-1", response.model_dump())
    received = receive_loop.receive("run-1", "task-1", to_actor="human", timeout_seconds=1)
    assert received.status == "responded"

    event_types = [e["event_type"] for e in events.query("run-1")]
    assert "message_queued" in event_types
    assert "message_delivered" in event_types
    assert "response_received" in event_types
