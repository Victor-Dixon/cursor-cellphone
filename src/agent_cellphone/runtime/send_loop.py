import time

from agent_cellphone.contracts.message import CommandMessage
from agent_cellphone.runtime.event_log import EventLog
from agent_cellphone.storage.artifact_store import ArtifactStore
from agent_cellphone.transport.base import TransportAdapter


RETRYABLE_FAILURE_CODES = {"FOCUS_FAILED", "INJECTION_FAILED"}


class SendLoop:
    def __init__(self, adapter: TransportAdapter, store: ArtifactStore, event_log: EventLog):
        self.adapter = adapter
        self.store = store
        self.event_log = event_log

    def send(self, message: CommandMessage, max_retries: int = 2, backoff_seconds: float = 0.01) -> dict:
        self.store.write_json(message.run_id, "commands", message.message_id, message.model_dump())
        self.event_log.emit("message_queued", message.run_id, message.task_id, message.to_agent, "queued", {"message_id": message.message_id})

        attempt = 1
        while True:
            self.event_log.emit("message_send_started", message.run_id, message.task_id, message.to_agent, "sending", {"attempt": attempt})
            result = self.adapter.deliver(message, attempt=attempt)
            if result.success:
                self.event_log.emit("message_delivered", message.run_id, message.task_id, message.to_agent, "delivered", result.details)
                status = "awaiting_response" if message.requires_response else "delivered"
                return {"status": status, "attempts": attempt, "delivery": result.model_dump()}

            self.event_log.emit(
                "message_delivery_failed",
                message.run_id,
                message.task_id,
                message.to_agent,
                "failed",
                {"failure_code": result.failure_code, "attempt": attempt, **result.details},
            )
            if attempt <= max_retries and result.failure_code in RETRYABLE_FAILURE_CODES:
                self.event_log.emit("retry_scheduled", message.run_id, message.task_id, message.to_agent, "retrying", {"next_attempt": attempt + 1})
                attempt += 1
                time.sleep(backoff_seconds * attempt)
                continue

            self.event_log.emit("transport_error", message.run_id, message.task_id, message.to_agent, "failed", {"failure_code": result.failure_code})
            return {"status": "failed", "attempts": attempt, "delivery": result.model_dump()}
