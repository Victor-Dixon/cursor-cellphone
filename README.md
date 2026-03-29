# Agent Cellphone

## What Agent Cellphone Is
Agent Cellphone is a transport adapter for Dream.OS v2. It handles structured send/receive/handoff message delivery and logs transport events to deterministic local artifacts.

## What Agent Cellphone Is Not
- Not Dream.OS orchestration core
- Not policy or domain-truth owner
- Not hidden memory-based coordination

## Architecture
- **Contracts** (`contracts/`): strict schema validation for command/response/handoff/event payloads.
- **Storage** (`storage/`): deterministic run-scoped artifact layout.
- **Runtime** (`runtime/`): send/receive/handoff loops and event emission.
- **Transport** (`transport/`): adapter interface and Cursor delivery implementation.

## Artifact Layout
All generated files are written under `.agent_cellphone/runs/{run_id}/`:
- `commands/`
- `responses/`
- `handoffs/`
- `events/events.jsonl`
- `logs/`
- `state/`

## CLI Usage
```bash
python -m agent_cellphone send --file examples/command.example.json
python -m agent_cellphone receive --run-id run-20260328-001 --task-id task-014
python -m agent_cellphone handoff --file examples/handoff.example.json
python -m agent_cellphone events --run-id run-20260328-001
python -m agent_cellphone smoke
```

## Transport Contract
Adapters must accept validated `CommandMessage`, return normalized `DeliveryResult`, and surface explicit failures (`TARGET_NOT_FOUND`, `FOCUS_FAILED`, `INJECTION_FAILED`, etc.).

## Development
```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .[dev]
```

## Smoke Tests
```bash
pytest -q
python -m agent_cellphone smoke
```

## Known Limitations
- Cursor adapter is local-automation oriented and currently deterministic/mockable for tests.
- Real UI automation wiring is intentionally isolated and minimal in MVP.
