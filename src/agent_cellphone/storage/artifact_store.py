import hashlib
import json
from pathlib import Path
from typing import Any

from agent_cellphone.storage.file_layout import ensure_run_layout, run_root


class ArtifactStore:
    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir

    def write_json(self, run_id: str, category: str, artifact_id: str, payload: dict[str, Any]) -> Path:
        root = ensure_run_layout(run_id, self.base_dir)
        target = root / category / f"{artifact_id}.json"
        target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return target

    def read_json(self, run_id: str, category: str, artifact_id: str) -> dict[str, Any]:
        path = run_root(run_id, self.base_dir) / category / f"{artifact_id}.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def exists(self, run_id: str, category: str, artifact_id: str) -> bool:
        path = run_root(run_id, self.base_dir) / category / f"{artifact_id}.json"
        return path.exists()

    @staticmethod
    def sha256_for_path(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()
