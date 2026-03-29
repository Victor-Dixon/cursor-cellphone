from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class HandoffMessage:
    handoff_id: str
    run_id: str
    task_id: str
    from_agent: str
    to_agent: str
    reason: str
    summary: list[str]
    required_action: str
    context_artifacts: list[str]
    created_at: str
    correlation_id: str

    @classmethod
    def model_validate(cls, payload: dict[str, Any]) -> "HandoffMessage":
        return cls(**payload)

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)
