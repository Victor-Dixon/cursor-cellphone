from agent_cellphone.contracts.handoff import HandoffMessage
from agent_cellphone.runtime.event_log import EventLog
from agent_cellphone.runtime.handoff_router import HandoffRouter
from agent_cellphone.storage.artifact_store import ArtifactStore
from agent_cellphone.transport.cursor_adapter import CursorTransportAdapter


def test_handoff_path(tmp_path):
    store = ArtifactStore(base_dir=tmp_path)
    events = EventLog(base_dir=tmp_path)
    router = HandoffRouter(CursorTransportAdapter(), store, events)

    handoff = HandoffMessage(
        handoff_id="handoff-1",
        run_id="run-h",
        task_id="task-h",
        from_agent="agent-3",
        to_agent="agent-5",
        reason="needs_review",
        summary=["check result"],
        required_action="review and respond",
        context_artifacts=["foo.md"],
        created_at="2026-03-28T15:00:00Z",
        correlation_id="corr-h",
    )
    result = router.route(handoff)
    assert result["status"] == "handed_off"

    event_types = [e["event_type"] for e in events.query("run-h")]
    assert "handoff_created" in event_types
    assert "handoff_delivered" in event_types
