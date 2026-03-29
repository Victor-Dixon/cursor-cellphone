from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class ArtifactRef:
    artifact_type: str
    path: str
    sha256: str
    created_at: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ArtifactRef":
        return cls(**payload)


@dataclass(slots=True)
class ResponseMessage:
    message_id: str
    run_id: str
    task_id: str
    from_agent: str
    to_actor: str
    status: str
    summary: list[str]
    artifacts: list[ArtifactRef]
    errors: list[str]
    created_at: str
    correlation_id: str

    def __post_init__(self) -> None:
        if self.status not in {"responded", "failed", "timed_out"}:
            raise ValueError(f"Unsupported status: {self.status}")

    @classmethod
    def model_validate(cls, payload: dict[str, Any]) -> "ResponseMessage":
        artifacts = [ArtifactRef.from_dict(x) if isinstance(x, dict) else x for x in payload.get("artifacts", [])]
        merged = {**payload, "artifacts": artifacts}
        return cls(**merged)

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)

    def model_dump_json(self, indent: int | None = None) -> str:
        import json

        return json.dumps(self.model_dump(), indent=indent)
