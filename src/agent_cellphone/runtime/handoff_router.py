from agent_cellphone.contracts.handoff import HandoffMessage
from agent_cellphone.contracts.message import CommandMessage
from agent_cellphone.runtime.event_log import EventLog
from agent_cellphone.storage.artifact_store import ArtifactStore
from agent_cellphone.transport.base import TransportAdapter


class HandoffRouter:
    def __init__(self, adapter: TransportAdapter, store: ArtifactStore, event_log: EventLog):
        self.adapter = adapter
        self.store = store
        self.event_log = event_log

    def route(self, handoff: HandoffMessage) -> dict:
        self.store.write_json(handoff.run_id, "handoffs", handoff.handoff_id, handoff.model_dump())
        self.event_log.emit("handoff_created", handoff.run_id, handoff.task_id, handoff.to_agent, "handed_off", {"handoff_id": handoff.handoff_id})

        bridge_command = CommandMessage(
            message_id=f"msg-{handoff.handoff_id}",
            run_id=handoff.run_id,
            task_id=handoff.task_id,
            from_actor=handoff.from_agent,
            to_agent=handoff.to_agent,
            message_type="handoff",
            payload={
                "reason": handoff.reason,
                "summary": handoff.summary,
                "required_action": handoff.required_action,
                "context_artifacts": handoff.context_artifacts,
            },
            priority="normal",
            created_at=handoff.created_at,
            timeout_seconds=600,
            requires_response=False,
            correlation_id=handoff.correlation_id,
        )
        result = self.adapter.deliver(bridge_command)
        if result.success:
            self.event_log.emit("handoff_delivered", handoff.run_id, handoff.task_id, handoff.to_agent, "handed_off", result.details)
            return {"status": "handed_off", "delivery": result.model_dump()}
        self.event_log.emit(
            "message_delivery_failed",
            handoff.run_id,
            handoff.task_id,
            handoff.to_agent,
            "failed",
            {"failure_code": "HANDOFF_DELIVERY_FAILED", "adapter_code": result.failure_code},
        )
        self.event_log.emit("transport_error", handoff.run_id, handoff.task_id, handoff.to_agent, "failed", {"failure_code": "HANDOFF_DELIVERY_FAILED"})
        return {"status": "failed", "delivery": result.model_dump()}
