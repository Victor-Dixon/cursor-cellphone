# Failure Modes

## Overview
This document describes transport-level failure visibility for Agent Cellphone MVP.

## Failure Codes
- `TARGET_NOT_FOUND`
- `FOCUS_FAILED`
- `INJECTION_FAILED`
- `RESPONSE_TIMEOUT`
- `INVALID_SCHEMA`
- `HANDOFF_DELIVERY_FAILED`
- `EVENT_WRITE_FAILED`
- `PERMISSION_ERROR`

## Detection Signals
- `message_delivery_failed` event with `failure_code`
- `transport_error` event for terminal transport failures
- `timeout_reached` event for response timeout
- non-zero CLI exit code

## Likely Causes
- Target agent alias not resolvable
- Cursor/UI focus acquisition failure
- Injection mechanism failure
- Missing response artifact before timeout
- Invalid artifact structure
- Filesystem permissions or event append failure

## Operator Action
1. Inspect `.agent_cellphone/runs/{run_id}/events/events.jsonl`.
2. Check command/handoff artifact payloads for target and schema fields.
3. Verify environment access and writable directories.
4. Retry only retryable failures (`FOCUS_FAILED`, `INJECTION_FAILED`).

## Retryability
- Retryable: `FOCUS_FAILED`, `INJECTION_FAILED`
- Non-retryable: `TARGET_NOT_FOUND`, `INVALID_SCHEMA`, `PERMISSION_ERROR`
- Timeout: operator-dependent; generally requires downstream agent inspection

## Escalation Guidance
Escalate when failures persist after deterministic retries, or when repeated `EVENT_WRITE_FAILED` / `PERMISSION_ERROR` prevent reliable audit trails.
