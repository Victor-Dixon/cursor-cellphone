from dataclasses import asdict, dataclass
from typing import Any

ALLOWED_MESSAGE_TYPES = {
    "command",
    "response",
    "handoff",
    "interrupt",
    "heartbeat",
    "error",
    "ack",
}


@dataclass(slots=True)
class CommandMessage:
    message_id: str
    run_id: str
    task_id: str
    from_actor: str
    to_agent: str
    message_type: str
    payload: dict[str, Any]
    priority: str
    created_at: str
    timeout_seconds: int
    requires_response: bool
    correlation_id: str

    def __post_init__(self) -> None:
        if self.message_type not in ALLOWED_MESSAGE_TYPES:
            raise ValueError(f"Unsupported message_type: {self.message_type}")
        if self.priority not in {"low", "normal", "high"}:
            raise ValueError(f"Unsupported priority: {self.priority}")

    @classmethod
    def model_validate(cls, payload: dict[str, Any]) -> "CommandMessage":
        return cls(**payload)

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)
