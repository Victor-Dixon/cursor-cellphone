import time

from agent_cellphone.contracts.response import ResponseMessage
from agent_cellphone.runtime.event_log import EventLog
from agent_cellphone.storage.artifact_store import ArtifactStore


class ReceiveLoop:
    def __init__(self, store: ArtifactStore, event_log: EventLog):
        self.store = store
        self.event_log = event_log

    def receive(self, run_id: str, task_id: str, to_actor: str, timeout_seconds: int = 1) -> ResponseMessage:
        start = time.time()
        artifact_id = task_id
        while time.time() - start <= timeout_seconds:
            if self.store.exists(run_id, "responses", artifact_id):
                payload = self.store.read_json(run_id, "responses", artifact_id)
                response = ResponseMessage.model_validate(payload)
                self.event_log.emit("response_received", run_id, task_id, response.from_agent, "responded", {"message_id": response.message_id})
                return response
            time.sleep(0.05)
        self.event_log.emit("timeout_reached", run_id, task_id, to_actor, "timed_out", {"failure_code": "RESPONSE_TIMEOUT"})
        raise TimeoutError(f"RESPONSE_TIMEOUT for run_id={run_id} task_id={task_id}")
