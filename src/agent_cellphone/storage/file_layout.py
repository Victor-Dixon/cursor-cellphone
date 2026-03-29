from pathlib import Path

ROOT_DIR = ".agent_cellphone"
SUBDIRS = ["commands", "responses", "handoffs", "events", "logs", "state"]


def run_root(run_id: str, base_dir: Path | None = None) -> Path:
    base = base_dir or Path.cwd()
    return base / ROOT_DIR / "runs" / run_id


def ensure_run_layout(run_id: str, base_dir: Path | None = None) -> Path:
    root = run_root(run_id, base_dir=base_dir)
    for name in SUBDIRS:
        (root / name).mkdir(parents=True, exist_ok=True)
    return root
