from abc import ABC, abstractmethod

from agent_cellphone.contracts.event import DeliveryResult
from agent_cellphone.contracts.message import CommandMessage


class TransportAdapter(ABC):
    @abstractmethod
    def deliver(self, message: CommandMessage, attempt: int = 1) -> DeliveryResult:
        raise NotImplementedError
