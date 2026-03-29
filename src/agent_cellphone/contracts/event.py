import json
from dataclasses import asdict, dataclass, field
from typing import Any

REQUIRED_EVENT_TYPES = {
    "message_queued",
    "message_send_started",
    "message_delivered",
    "message_delivery_failed",
    "response_received",
    "handoff_created",
    "handoff_delivered",
    "retry_scheduled",
    "timeout_reached",
    "interrupt_requested",
    "transport_error",
}


@dataclass(slots=True)
class EventRecord:
    event_id: str
    event_type: str
    run_id: str
    task_id: str
    agent_id: str
    status: str
    timestamp: str
    details: dict[str, Any]

    def __post_init__(self) -> None:
        if self.event_type not in REQUIRED_EVENT_TYPES:
            raise ValueError(f"Unsupported event_type: {self.event_type}")

    def model_dump_json(self) -> str:
        return json.dumps(asdict(self))


@dataclass(slots=True)
class DeliveryResult:
    success: bool
    delivery_status: str
    attempt_count: int
    failure_code: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)
