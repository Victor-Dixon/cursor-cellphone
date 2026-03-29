from agent_cellphone.contracts.event import DeliveryResult
from agent_cellphone.contracts.message import CommandMessage
from agent_cellphone.transport.base import TransportAdapter


class CursorTransportAdapter(TransportAdapter):
    """Cursor-focused delivery adapter.

    MVP implementation uses deterministic environment checks and returns explicit
    failure codes without swallowing transport issues.
    """

    def __init__(self, known_agents: set[str] | None = None, should_focus: bool = True, should_inject: bool = True):
        self.known_agents = known_agents or {"agent-1", "agent-2", "agent-3", "agent-4", "agent-5"}
        self.should_focus = should_focus
        self.should_inject = should_inject

    def deliver(self, message: CommandMessage, attempt: int = 1) -> DeliveryResult:
        if message.to_agent not in self.known_agents:
            return DeliveryResult(
                success=False,
                delivery_status="failed",
                attempt_count=attempt,
                failure_code="TARGET_NOT_FOUND",
                details={"to_agent": message.to_agent},
            )
        if not self.should_focus:
            return DeliveryResult(
                success=False,
                delivery_status="failed",
                attempt_count=attempt,
                failure_code="FOCUS_FAILED",
                details={"to_agent": message.to_agent},
            )
        if not self.should_inject:
            return DeliveryResult(
                success=False,
                delivery_status="failed",
                attempt_count=attempt,
                failure_code="INJECTION_FAILED",
                details={"message_id": message.message_id},
            )
        return DeliveryResult(
            success=True,
            delivery_status="delivered",
            attempt_count=attempt,
            details={"adapter": "cursor", "to_agent": message.to_agent},
        )
