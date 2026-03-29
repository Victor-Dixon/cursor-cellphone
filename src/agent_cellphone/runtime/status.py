"""Shared status constants."""

ALLOWED_STATUSES = {
    "queued",
    "sending",
    "delivered",
    "awaiting_response",
    "responded",
    "handed_off",
    "retrying",
    "timed_out",
    "failed",
    "cancelled",
}
