import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from agent_cellphone.contracts.event import EventRecord
from agent_cellphone.storage.file_layout import ensure_run_layout, run_root


class EventLog:
    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir

    def _path(self, run_id: str) -> Path:
        ensure_run_layout(run_id, self.base_dir)
        return run_root(run_id, self.base_dir) / "events" / "events.jsonl"

    def emit(
        self,
        event_type: str,
        run_id: str,
        task_id: str,
        agent_id: str,
        status: str,
        details: dict,
    ) -> EventRecord:
        record = EventRecord(
            event_id=f"evt-{uuid4().hex[:12]}",
            event_type=event_type,
            run_id=run_id,
            task_id=task_id,
            agent_id=agent_id,
            status=status,
            timestamp=datetime.now(timezone.utc).isoformat(),
            details=details,
        )
        with self._path(run_id).open("a", encoding="utf-8") as f:
            f.write(record.model_dump_json() + "\n")
        return record

    def query(self, run_id: str, **filters: str) -> list[dict]:
        path = self._path(run_id)
        if not path.exists():
            return []
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if all(str(row.get(k)) == v for k, v in filters.items()):
                rows.append(row)
        return rows
