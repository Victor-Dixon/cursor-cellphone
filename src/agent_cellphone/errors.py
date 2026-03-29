"""Error primitives for transport failures."""

from dataclasses import dataclass


@dataclass(slots=True)
class TransportError(Exception):
    code: str
    message: str
    retryable: bool = False

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"
