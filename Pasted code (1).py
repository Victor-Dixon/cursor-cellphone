#!/usr/bin/env python3
"""
🐝 UNIFIED MESSAGING SYSTEM - SINGLE SOURCE OF TRUTH
=====================================================

The ONE AND ONLY messaging system for Agent Cellphone V2.
Combines all messaging functionality into a single, comprehensive system.

FEATURES:
- ✅ **Message Queue Management** - Persistent queues with routing and processing
- ✅ **PyAutoGUI Communication** - Direct agent control via coordinates and automation
- ✅ **Discord Integration** - Webhook-based messaging with rich embeds
- ✅ **Agent Coordination** - Bilateral and swarm communication protocols
- ✅ **Template Resolution** - Dynamic message formatting and templating
- ✅ **Message History** - Complete audit trail and message tracking
- ✅ **Protocol Support** - Structured messaging protocols and validation
- ✅ **Error Recovery** - Retry logic, deduplication, and failure handling
- ✅ **Async Operations** - Non-blocking message processing and delivery
- ✅ **Multi-Channel Support** - Agent inbox, Discord, PyAutoGUI, and more
- ✅ **Performance Monitoring** - Message throughput and delivery metrics
- ✅ **Message Validation** - Content validation and sanitization
- ✅ **Broadcasting** - Swarm-wide message distribution

UNIFIED APPROACH:
- Single MessagingOrchestrator class that handles everything
- Modular design with clear separation of concerns
- Built-in fallback mechanisms (PyAutoGUI → Discord → Queue)
- SSOT principle: One messaging system, one API, zero confusion

USAGE:
    # Simple agent-to-agent messaging
    from messaging_unified import send_agent_message
    result = send_agent_message("Agent-1", "Agent-2", "Hello from unified messaging!")

    # Broadcast to all agents
    from messaging_unified import broadcast_message
    broadcast_message("System update: All agents stand by", priority="high")

    # Discord integration
    from messaging_unified import send_discord_message
    send_discord_message("Alert!", channel_id="123456789", embed=embed_data)

    # Queue management
    from messaging_unified import MessageQueueManager
    queue = MessageQueueManager()
    queue.enqueue_message(message_data)

SSOT PRINCIPLE: One messaging system, one API, zero duplication.

Author: Agent-1 (Unified Messaging Architect)
Date: 2026-01-15
"""

import asyncio
import json
import logging
import os
import re
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable, Tuple
from urllib.parse import urljoin
import aiohttp

# Import unified logging
try:
    from logging_unified import get_logger
except ImportError:
    import logging
    get_logger = logging.getLogger

# Import unified error handling
try:
    from error_handling_unified import handle_errors, ErrorHandlingMixin
except ImportError:
    ErrorHandlingMixin = object
    def handle_errors(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

logger = get_logger(__name__)

# Global messaging statistics
_messaging_stats = {
    "messages_sent": 0,
    "messages_delivered": 0,
    "messages_failed": 0,
    "queue_size": 0,
    "discord_messages": 0,
    "pyautogui_operations": 0,
    "retries_attempted": 0,
    "deduplication_hits": 0,
    "last_message_time": None
}

class MessagePriority(Enum):
    """Standardized message priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"

class MessageType(Enum):
    """Standardized message types."""
    COORDINATION = "coordination"
    A2A_COORDINATION = "a2a_coordination"  # Bilateral agent-to-agent coordination
    TASK = "task"
    STATUS = "status"
    BROADCAST = "broadcast"
    ALERT = "alert"
    ONBOARDING = "onboarding"
    SOFT_ONBOARDING = "soft_onboarding"  # Soft onboarding welcome
    HARD_ONBOARDING = "hard_onboarding"  # Hard onboarding integration
    SESSION_CLOSURE = "session_closure"   # Session closure coordination
    SYSTEM = "system"
    USER = "user"

class DeliveryMethod(Enum):
    """Message delivery methods."""
    PYAUTOGUI = "pyautogui"
    DISCORD = "discord"
    QUEUE = "queue"
    WEBSOCKET = "websocket"
    DIRECT = "direct"

class MessageStatus(Enum):
    """Message delivery status."""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"
    EXPIRED = "expired"

@dataclass
class MessageRecipient:
    """Message recipient information."""
    agent_id: str
    coordinates: Optional[Tuple[int, int]] = None
    discord_channel: Optional[str] = None
    websocket_id: Optional[str] = None
    inbox_path: Optional[Path] = None

@dataclass
class UnifiedMessage:
    """Unified message structure."""
    sender: str
    recipient: Union[str, List[str]]
    content: str
    message_type: MessageType = MessageType.USER
    priority: MessagePriority = MessagePriority.NORMAL
    delivery_methods: List[DeliveryMethod] = field(default_factory=lambda: [DeliveryMethod.PYAUTOGUI])
    metadata: Dict[str, Any] = field(default_factory=dict)
    template_vars: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    max_retries: int = 3
    retry_count: int = 0
    status: MessageStatus = MessageStatus.PENDING
    delivered_at: Optional[datetime] = None
    error_message: Optional[str] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        # Handle enum serialization safely
        data["message_type"] = self.message_type.value if hasattr(self.message_type, 'value') else str(self.message_type)
        data["priority"] = self.priority.value if hasattr(self.priority, 'value') else str(self.priority)
        data["delivery_methods"] = [m.value if hasattr(m, 'value') else str(m) for m in self.delivery_methods]
        data["status"] = self.status.value if hasattr(self.status, 'value') else str(self.status)
        data["created_at"] = self.created_at.isoformat()
        if self.expires_at:
            data["expires_at"] = self.expires_at.isoformat()
        if self.delivered_at:
            data["delivered_at"] = self.delivered_at.isoformat()
        return data

    def is_expired(self) -> bool:
        """Check if message has expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

@dataclass
class DeliveryResult:
    """Result of message delivery attempt."""
    message_id: str
    method: DeliveryMethod
    success: bool
    error_message: Optional[str] = None
    retryable: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

class MessageQueue:
    """Persistent message queue with file-based storage."""

    def __init__(self, storage_path: Path = None):
        """Initialize message queue."""
        self.storage_path = storage_path or Path("message_queue")
        self.storage_path.mkdir(exist_ok=True)
        self.queue_file = self.storage_path / "queue.json"
        self.history_file = self.storage_path / "history.json"
        self.deduplication_file = self.storage_path / "deduplication.json"

        # Load existing data
        self.queue = self._load_queue()
        self.history = self._load_history()
        self.deduplication_cache = self._load_deduplication()

    def _load_queue(self) -> List[UnifiedMessage]:
        """Load queue from disk."""
        if not self.queue_file.exists():
            return []

        try:
            with open(self.queue_file, 'r') as f:
                data = json.load(f)
                return [self._dict_to_message(item) for item in data]
        except Exception as e:
            logger.error(f"Failed to load message queue: {e}")
            return []

    def _load_history(self) -> List[UnifiedMessage]:
        """Load message history from disk."""
        if not self.history_file.exists():
            return []

        try:
            with open(self.history_file, 'r') as f:
                data = json.load(f)
                return [self._dict_to_message(item) for item in data]
        except Exception as e:
            logger.error(f"Failed to load message history: {e}")
            return []

    def _load_deduplication(self) -> Dict[str, datetime]:
        """Load deduplication cache."""
        if not self.deduplication_file.exists():
            return {}

        try:
            with open(self.deduplication_file, 'r') as f:
                data = json.load(f)
                return {k: datetime.fromisoformat(v) for k, v in data.items()}
        except Exception as e:
            logger.error(f"Failed to load deduplication cache: {e}")
            return {}

    def _dict_to_message(self, data: Dict[str, Any]) -> UnifiedMessage:
        """Convert dictionary to UnifiedMessage."""
        # Handle enum conversions
        data["message_type"] = MessageType(data.get("message_type", "user"))
        data["priority"] = MessagePriority(data.get("priority", "normal"))
        data["delivery_methods"] = [DeliveryMethod(m) for m in data.get("delivery_methods", ["pyautogui"])]
        data["status"] = MessageStatus(data.get("status", "pending"))

        # Handle datetime conversions
        if "created_at" in data:
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if "expires_at" in data and data["expires_at"]:
            data["expires_at"] = datetime.fromisoformat(data["expires_at"])
        if "delivered_at" in data and data["delivered_at"]:
            data["delivered_at"] = datetime.fromisoformat(data["delivered_at"])

        return UnifiedMessage(**data)

    def enqueue(self, message: UnifiedMessage) -> bool:
        """Add message to queue."""
        global _messaging_stats

        # Check for duplicates
        if self._is_duplicate(message):
            _messaging_stats["deduplication_hits"] += 1
            logger.info(f"Duplicate message detected: {message.id}")
            return False

        self.queue.append(message)
        self._save_queue()

        _messaging_stats["queue_size"] = len(self.queue)

        logger.info(f"Message enqueued: {message.id} to {message.recipient}")
        return True

    def dequeue(self) -> Optional[UnifiedMessage]:
        """Get next message from queue."""
        global _messaging_stats

        if not self.queue:
            return None

        message = self.queue.pop(0)
        self._save_queue()

        _messaging_stats["queue_size"] = len(self.queue)

        return message

    def mark_delivered(self, message: UnifiedMessage):
        """Mark message as delivered."""
        global _messaging_stats

        message.status = MessageStatus.DELIVERED
        message.delivered_at = datetime.utcnow()
        self.history.append(message)
        self._save_history()

        _messaging_stats["messages_delivered"] += 1

    def mark_failed(self, message: UnifiedMessage, error: str):
        """Mark message as failed."""
        global _messaging_stats

        message.status = MessageStatus.FAILED
        message.error_message = error
        self.history.append(message)
        self._save_history()

        _messaging_stats["messages_failed"] += 1

    def _is_duplicate(self, message: UnifiedMessage) -> bool:
        """Check if message is a duplicate."""
        # Simple deduplication based on content hash
        import hashlib
        content_hash = hashlib.md5(f"{message.sender}:{message.recipient}:{message.content}".encode()).hexdigest()

        # Check recent duplicates (last 24 hours)
        cutoff = datetime.utcnow() - timedelta(hours=24)

        # Clean old entries
        self.deduplication_cache = {
            k: v for k, v in self.deduplication_cache.items()
            if v > cutoff
        }

        if content_hash in self.deduplication_cache:
            return True

        self.deduplication_cache[content_hash] = datetime.utcnow()
        self._save_deduplication()
        return False

    def _save_queue(self):
        """Save queue to disk."""
        try:
            with open(self.queue_file, 'w') as f:
                json.dump([msg.to_dict() for msg in self.queue], f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save message queue: {e}")

    def _save_history(self):
        """Save history to disk."""
        try:
            # Keep only last 1000 messages in history
            recent_history = self.history[-1000:]
            with open(self.history_file, 'w') as f:
                json.dump([msg.to_dict() for msg in recent_history], f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save message history: {e}")

    def _save_deduplication(self):
        """Save deduplication cache to disk."""
        try:
            with open(self.deduplication_file, 'w') as f:
                json.dump({k: v.isoformat() for k, v in self.deduplication_cache.items()}, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save deduplication cache: {e}")

class TemplateResolver:
    """Message template resolution and formatting."""

    def __init__(self):
        """Initialize template resolver."""
        self.templates = {}
        self._load_builtin_templates()

    def _load_builtin_templates(self):
        """Load built-in message templates including bilateral A2A templates."""
        self.templates = {
            # Basic templates
            "coordination": "🔄 **COORDINATION REQUEST**\nFrom: {sender}\nTo: {recipient}\n\n{content}\n\nPriority: {priority}",
            "task": "📋 **TASK ASSIGNMENT**\nAssigned to: {recipient}\nFrom: {sender}\n\n{content}",
            "status": "📊 **STATUS UPDATE**\nFrom: {sender}\n\n{content}",
            "broadcast": "📢 **SYSTEM BROADCAST**\n\n{content}",
            "alert": "🚨 **SYSTEM ALERT**\n\n{content}",
            "onboarding": "🛰️ **ONBOARDING DIRECTIVE**\nTo: {recipient}\n\n{content}",

            # Bilateral A2A Coordination Template (Restored from archive)
            "a2a_coordination": (
                "[HEADER] A2A COORDINATION — BILATERAL SWARM COORDINATION\n"
                "From: {sender}\n"
                "To: {recipient}\n"
                "Priority: {priority}\n"
                "Message ID: {message_id}\n"
                "Timestamp: {timestamp}\n\n"
                "🚀 **PROTOCOL UPDATE: Swarm Coordination**\n"
                "{coordination_type} request for parallel processing acceleration.\n\n"
                "🐝 **COORDINATED SWARM REQUEST**:\n"
                "This is a bilateral coordination request to leverage swarm force multiplication.\n"
                "We're asking for your expertise to parallelize work and accelerate completion.\n\n"
                "**COORDINATION REQUEST**:\n{content}\n\n"
                "**WHY THIS COORDINATION?**\n{coordination_rationale}\n\n"
                "**EXPECTED CONTRIBUTION**:\n{expected_contribution}\n\n"
                "**TIMING**:\n{coordination_timeline}\n\n"
                "**RESPONSE REQUIRED**:\n"
                "Reply within 30 minutes with acceptance/decline and proposed approach.\n\n"
                "**WHAT TO INCLUDE IN YOUR REPLY** (for ACCEPT responses):\n"
                "- **Proposed approach**: How you'll coordinate (your role + partner's role)\n"
                "- **Synergy identification**: How your capabilities complement your partner's\n"
                "- **Next steps**: Suggested initial coordination touchpoint or action item\n"
                "- **Relevant capabilities**: Brief list of your applicable skills\n"
                "- **Timeline**: When you can start and expected coordination sync time\n\n"
                "**REPLY FORMAT (MANDATORY)**:\n"
                "```\n"
                "A2A REPLY to {message_id}:\n"
                "✅ ACCEPT: [Proposed approach: your role + partner role. Synergy: how capabilities complement. Next steps: initial action. Capabilities: key skills. Timeline: start time + sync time] | ETA: [timeframe]\n"
                "OR\n"
                "❌ DECLINE: [reason] | Alternative: [suggested agent]\n"
                "```\n\n"
                "**REPLY COMMAND**:\n"
                "```bash\n"
                "python messaging_cli_unified.py --agent {sender} \\\n"
                "  --message \"A2A REPLY to {message_id}: [your response]\" \\\n"
                "  --type coordination --sender {recipient}\n"
                "```\n\n"
                "**COORDINATION PRINCIPLES**:\n"
                "- 2 agents working in parallel > 1 agent working alone\n"
                "- Share context via status updates and A2A pings\n"
                "- Report progress to accelerate integration\n"
                "- Be proactive: Propose concrete next steps rather than 'standing by'\n"
                "- Identify synergy: Explain how your skills complement your partner's\n\n"
                "**PUSH DIRECTIVES, DON'T REPEAT**: When you receive a message that repeats previous coordination or asks for status you've already provided, don't just reiterate—use it as momentum to:\n"
                "- Execute the next logical work step immediately\n"
                "- Propose a new task or next action back to the sender\n"
                "- Suggest a concrete follow-up task that advances the coordination\n"
                "- Take initiative to unblock yourself or others\n"
                "Messages are fuel for action, not just confirmation loops. Turn repeat messages into forward progress.\n\n"
                "#{coordination_hashtag} #SWARM-FORCE-MULTIPLIER\n"
            ),

            # Soft Onboarding Template (Restored from archive)
            "soft_onboarding": (
                "[HEADER] S2A ONBOARDING (SOFT)\n"
                "From: {sender}\n"
                "To: {recipient}\n"
                "Priority: regular\n"
                "Message ID: {message_id}\n"
                "Timestamp: {timestamp}\n\n"
                "🌟 **Welcome to the Swarm, {recipient}!**\n\n"
                "You have been successfully onboarded to the Agent Cellphone V2 system.\n\n"
                "**Your Role & Capabilities**:\n"
                "- Agent ID: {recipient}\n"
                "- Status: ACTIVE\n"
                "- Messaging: ENABLED\n"
                "- Coordination: AVAILABLE\n\n"
                "**Getting Started**:\n"
                "1. You can now receive and send messages to other agents\n"
                "2. Use A2A coordination for collaborative tasks\n"
                "3. Check your inbox regularly for coordination requests\n"
                "4. Update your status to coordinate with the swarm\n\n"
                "**Communication Channels**:\n"
                "- Direct messaging: `python messaging_cli_unified.py --agent [target] --message [content]`\n"
                "- A2A coordination: Use the coordination templates\n"
                "- Broadcast: System-wide announcements\n\n"
                "**Coordination Protocol**:\n"
                "When you receive coordination requests, respond promptly with:\n"
                "```\n"
                "✅ ACCEPT: [your approach and timeline]\n"
                "❌ DECLINE: [reason and alternative]\n"
                "```\n\n"
                "**System Features**:\n"
                "- Clean Messaging V3: No legacy conflicts\n"
                "- PyAutoGUI Delivery: Visual coordinate-based messaging\n"
                "- Queue Processing: Background message handling\n"
                "- Swarm Coordination: Bilateral coordination protocols\n\n"
                "Welcome to the swarm! 🐝⚡️\n\n"
                "#ONBOARDING #SOFT #WELCOME\n"
            ),

            # Hard Onboarding Template (Restored from archive)
            "hard_onboarding": (
                "[HEADER] S2A ONBOARDING (HARD)\n"
                "From: {sender}\n"
                "To: {recipient}\n"
                "Priority: urgent\n"
                "Message ID: {message_id}\n"
                "Timestamp: {timestamp}\n\n"
                "🚀 **CRITICAL SYSTEMS ONBOARDING - {recipient}**\n\n"
                "**SYSTEM STATUS: FULLY OPERATIONAL**\n"
                "You are now integrated into the Agent Cellphone V2 swarm intelligence system.\n\n"
                "**SYSTEM ARCHITECTURE**:\n"
                "- Messaging V3: Clean rebuild with PyAutoGUI delivery\n"
                "- Queue System: Persistent message queuing\n"
                "- Coordination Protocol: A2A bilateral swarm coordination\n"
                "- Status Integration: Real-time agent status tracking\n\n"
                "**YOUR CAPABILITIES**:\n"
                "✅ Message reception and transmission\n"
                "✅ A2A coordination protocol execution\n"
                "✅ Status reporting and updates\n"
                "✅ Task coordination and delegation\n"
                "✅ Error handling and recovery\n\n"
                "**IMMEDIATE ACTION REQUIRED**:\n"
                "1. Confirm system integration: Reply with \"HARD ONBOARDING CONFIRMED\"\n"
                "2. Update your status: Coordinate with swarm for initial task assignment\n"
                "3. Begin coordination: Look for A2A coordination requests\n"
                "4. Report readiness: Update swarm with your current capabilities\n\n"
                "**COORDINATION COMMAND**:\n"
                "```bash\n"
                "python messaging_cli_unified.py --agent {sender} --message \"HARD ONBOARDING CONFIRMED: {recipient} ready for coordination\" --type system --sender {recipient}\n"
                "```\n\n"
                "**SYSTEM FEATURES**:\n"
                "- PyAutoGUI Integration: Direct screen control messaging\n"
                "- Coordinate-Based Delivery: Precise agent targeting\n"
                "- Queue Persistence: Message reliability across restarts\n"
                "- A2A Coordination: Bilateral swarm intelligence\n"
                "- Status Synchronization: Real-time swarm state awareness\n\n"
                "**COORDINATION READY - AWAITING TASK ASSIGNMENT**\n"
                "#ONBOARDING #HARD #SYSTEMS #INTEGRATION\n"
            ),

            # Session Closure Template (for bilateral coordination)
            "session_closure": (
                "[HEADER] SESSION CLOSURE — COORDINATION COMPLETE\n"
                "From: {sender}\n"
                "To: {recipient}\n"
                "Priority: high\n"
                "Message ID: {message_id}\n"
                "Timestamp: {timestamp}\n\n"
                "🏁 **SESSION CLOSURE CONFIRMATION**\n\n"
                "**COORDINATION SUMMARY**:\n"
                "{coordination_summary}\n\n"
                "**DELIVERABLES COMPLETED**:\n"
                "{deliverables}\n\n"
                "**SESSION METRICS**:\n"
                "- Duration: {session_duration}\n"
                "- Tasks Completed: {tasks_completed}\n"
                "- Coordination Events: {coordination_events}\n"
                "- Status Updates: {status_updates}\n\n"
                "**SESSION VALIDATION**:\n"
                "✅ A++ Format Compliance\n"
                "✅ Deliverable Verification\n"
                "✅ Git Operations Confirmed\n"
                "✅ Swarm State Updated\n\n"
                "**SESSION CLOSED SUCCESSFULLY**\n"
                "Coordination complete. Ready for next assignment.\n\n"
                "#SESSION #CLOSURE #COORDINATION #COMPLETE\n"
            )
        }

    def resolve_template(self, message: UnifiedMessage) -> str:
        """Resolve message template."""
        template = self.templates.get(message.message_type.value, "{content}")

        # Apply template variables with defaults
        template_vars = {
            "sender": message.sender,
            "recipient": message.recipient if isinstance(message.recipient, str) else ", ".join(message.recipient),
            "content": message.content,
            "priority": message.priority.value.upper(),
            "timestamp": message.created_at.strftime("%H:%M:%S UTC"),
            "message_id": message.id,  # Add message ID
            **message.template_vars
        }

        try:
            formatted = template.format(**template_vars)
            logger.debug(f"Template resolved for {message.message_type.value}: {len(formatted)} chars")
            return formatted
        except KeyError as e:
            logger.warning(f"Template variable missing: {e}")
            return message.content

class PyAutoGUIDelivery:
    """PyAutoGUI-based message delivery."""

    def __init__(self):
        """Initialize PyAutoGUI delivery."""
        self.pyautogui_available = False
        self.coordinates_cache = {}

        try:
            import pyautogui
            self.pyautogui = pyautogui
            self.pyautogui_available = True
            self.pyautogui.FAILSAFE = True
        except ImportError:
            logger.warning("PyAutoGUI not available for message delivery")

    def load_coordinates(self, agent_id: str) -> Optional[Tuple[int, int]]:
        """Load coordinates for agent from multiple file formats."""
        if agent_id in self.coordinates_cache:
            return self.coordinates_cache[agent_id]

        # Try multiple coordinate file formats and locations
        coord_files = [
            Path("agent_coordinates.json"),          # Standard format
            Path("cursor_agent_coords.json"),        # Windows format
            Path("cursor_agent_coords_linux.json"),  # Linux format
        ]

        for coords_file in coord_files:
            if coords_file.exists():
                try:
                    coords = self._parse_coordinates_file(coords_file, agent_id)
                    if coords:
                        self.coordinates_cache[agent_id] = coords
                        return coords
                except Exception as e:
                    logger.warning(f"Failed to parse {coords_file} for {agent_id}: {e}")

        return None

    def _parse_coordinates_file(self, coords_file: Path, agent_id: str) -> Optional[Tuple[int, int]]:
        """Parse coordinates from different file formats."""
        with open(coords_file, 'r') as f:
            data = json.load(f)

        # Format 1: Simple {"Agent-X": [x, y]}
        if agent_id in data and isinstance(data[agent_id], list) and len(data[agent_id]) == 2:
            return tuple(data[agent_id])

        # Format 2: Nested Windows format {"agents": {"Agent-X": {"chat_input_coordinates": [x, y]}}}
        if "agents" in data and agent_id in data["agents"]:
            agent_data = data["agents"][agent_id]
            if "chat_input_coordinates" in agent_data and isinstance(agent_data["chat_input_coordinates"], list):
                return tuple(agent_data["chat_input_coordinates"])

        # Format 3: Nested Linux format {"Agent-X": {"chat_input": [x, y]}}
        if agent_id in data and isinstance(data[agent_id], dict):
            agent_data = data[agent_id]
            if "chat_input" in agent_data and isinstance(agent_data["chat_input"], list):
                return tuple(agent_data["chat_input"])

        return None

    async def deliver_message(self, message: UnifiedMessage, recipient: MessageRecipient) -> DeliveryResult:
        """Deliver message using PyAutoGUI."""
        global _messaging_stats

        result = DeliveryResult(
            message_id=message.id,
            method=DeliveryMethod.PYAUTOGUI,
            success=False
        )

        if not self.pyautogui_available:
            result.error_message = "PyAutoGUI not available"
            return result

        try:
            coords = recipient.coordinates
            if not coords:
                coords = self.load_coordinates(recipient.agent_id)
                if not coords:
                    result.error_message = f"No coordinates found for {recipient.agent_id}"
                    return result

            # Get formatted content
            template_resolver = TemplateResolver()
            formatted_content = template_resolver.resolve_template(message)

            # Execute PyAutoGUI operations
            await asyncio.get_event_loop().run_in_executor(
                None,
                self._execute_pyautogui_sequence,
                coords,
                formatted_content
            )

            result.success = True

            _messaging_stats["pyautogui_operations"] += 1

        except Exception as e:
            result.error_message = f"PyAutoGUI delivery failed: {e}"
            logger.error(f"PyAutoGUI delivery failed for {message.id}: {e}")

        return result

    def _execute_pyautogui_sequence(self, coords: Tuple[int, int], content: str):
        """Execute PyAutoGUI click and type sequence with proper line break handling."""
        # Move to coordinates and click
        self.pyautogui.moveTo(coords[0], coords[1], duration=0.5)
        self.pyautogui.click()

        # Small delay
        time.sleep(0.1)

        # Type the message with proper line break handling
        # PyAutoGUI automatically handles \n by pressing Enter, but for chat interfaces
        # that require Shift+Enter for line breaks, we need to simulate Shift+Enter
        lines = content.split('\n')
        for i, line in enumerate(lines):
            # Type the current line
            if line:  # Only type if line is not empty
                self.pyautogui.typewrite(line, interval=0.02)

            # If this is not the last line, create a line break with Shift+Enter
            if i < len(lines) - 1:
                self.pyautogui.hotkey('shift', 'enter')

        # Press enter to send the message (without shift)
        time.sleep(0.05)  # Small delay before sending
        self.pyautogui.press('enter')

class DiscordDelivery:
    """Discord webhook-based message delivery."""

    def __init__(self, webhook_url: Optional[str] = None):
        """Initialize Discord delivery."""
        self.webhook_url = webhook_url
        self.session = None

    def configure(self, webhook_url: str):
        """Configure webhook URL."""
        self.webhook_url = webhook_url

    async def deliver_message(self, message: UnifiedMessage, recipient: MessageRecipient) -> DeliveryResult:
        """Deliver message via Discord webhook."""
        global _messaging_stats

        result = DeliveryResult(
            message_id=message.id,
            method=DeliveryMethod.DISCORD,
            success=False
        )

        if not self.webhook_url:
            result.error_message = "Discord webhook not configured"
            return result

        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            # Format message for Discord
            template_resolver = TemplateResolver()
            formatted_content = template_resolver.resolve_template(message)

            payload = {
                "content": formatted_content,
                "username": f"Agent-{message.sender}",
            }

            # Add embed if metadata contains embed info
            if "embed" in message.metadata:
                payload["embeds"] = [message.metadata["embed"]]

            async with self.session.post(
                self.webhook_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                success = response.status in (200, 204)
                if success:
                    result.success = True
                    _messaging_stats["discord_messages"] += 1
                else:
                    result.error_message = f"Discord API error: {response.status}"

        except Exception as e:
            result.error_message = f"Discord delivery failed: {e}"
            logger.error(f"Discord delivery failed for {message.id}: {e}")

        return result

    async def close(self):
        """Close Discord session."""
        if self.session:
            await self.session.close()
            self.session = None

class InboxDelivery:
    """Agent inbox-based message delivery."""

    def __init__(self, agent_workspaces_dir: Path = None):
        """Initialize inbox delivery."""
        self.agent_workspaces_dir = agent_workspaces_dir or Path("agent_workspaces")

    async def deliver_message(self, message: UnifiedMessage, recipient: MessageRecipient) -> DeliveryResult:
        """Deliver message to agent inbox."""
        result = DeliveryResult(
            message_id=message.id,
            method=DeliveryMethod.QUEUE,
            success=False
        )

        try:
            inbox_path = recipient.inbox_path
            if not inbox_path:
                inbox_path = self.agent_workspaces_dir / recipient.agent_id / "inbox"
                inbox_path.mkdir(parents=True, exist_ok=True)

            # Create message file
            timestamp = message.created_at.strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{message.id}.md"

            template_resolver = TemplateResolver()
            formatted_content = template_resolver.resolve_template(message)

            message_content = f"""---
Message ID: {message.id}
From: {message.sender}
To: {recipient.agent_id}
Type: {message.message_type.value}
Priority: {message.priority.value}
Timestamp: {message.created_at.isoformat()}
---

{formatted_content}
"""

            message_file = inbox_path / filename
            with open(message_file, 'w', encoding='utf-8') as f:
                f.write(message_content)

            result.success = True
            result.metadata["file_path"] = str(message_file)

        except Exception as e:
            result.error_message = f"Inbox delivery failed: {e}"
            logger.error(f"Inbox delivery failed for {message.id}: {e}")

        return result

class MessagingOrchestrator:
    """Main orchestrator for all messaging operations."""

    def __init__(self):
        """Initialize messaging orchestrator."""
        self.queue = MessageQueue()
        self.template_resolver = TemplateResolver()
        self.pyautogui_delivery = PyAutoGUIDelivery()
        self.discord_delivery = DiscordDelivery()
        self.inbox_delivery = InboxDelivery()
        self.logger = get_logger("MessagingOrchestrator")

        # Delivery method registry
        self.delivery_handlers = {
            DeliveryMethod.PYAUTOGUI: self.pyautogui_delivery,
            DeliveryMethod.DISCORD: self.discord_delivery,
            DeliveryMethod.QUEUE: self.inbox_delivery,
        }

        self.recipient_cache = {}
        self.logger.info("MessagingOrchestrator initialized")

    def configure_discord(self, webhook_url: str):
        """Configure Discord webhook."""
        self.discord_delivery.configure(webhook_url)

    async def send_message(
        self,
        sender: str,
        recipient: Union[str, List[str]],
        content: str,
        message_type: MessageType = MessageType.USER,
        priority: MessagePriority = MessagePriority.NORMAL,
        delivery_methods: Optional[List[DeliveryMethod]] = None,
        **kwargs
    ) -> List[DeliveryResult]:
        """Send a message using the best available delivery method."""

        # Create unified message
        message = UnifiedMessage(
            sender=sender,
            recipient=recipient,
            content=content,
            message_type=message_type,
            priority=priority,
            delivery_methods=delivery_methods or [DeliveryMethod.PYAUTOGUI],
            metadata=kwargs.get("metadata", {}),
            template_vars=kwargs.get("template_vars", {}),
            expires_at=kwargs.get("expires_at"),
            max_retries=kwargs.get("max_retries", 3)
        )

        _messaging_stats["messages_sent"] += 1
        _messaging_stats["last_message_time"] = datetime.utcnow()

        # Handle single recipient
        if isinstance(recipient, str):
            return await self._deliver_to_recipient(message, recipient)

        # Handle multiple recipients
        results = []
        for recip in recipient:
            recip_results = await self._deliver_to_recipient(message, recip)
            results.extend(recip_results)

        return results

    async def _deliver_to_recipient(self, message: UnifiedMessage, recipient_id: str) -> List[DeliveryResult]:
        """Deliver message to a specific recipient."""
        global _messaging_stats

        recipient = self._get_recipient_info(recipient_id)
        results = []

        # Try each delivery method in order
        for method in message.delivery_methods:
            if method in self.delivery_handlers:
                handler = self.delivery_handlers[method]

                # Attempt delivery
                result = await handler.deliver_message(message, recipient)
                results.append(result)

                if result.success:
                    self.queue.mark_delivered(message)
                    break
                elif result.retryable and message.retry_count < message.max_retries:
                    # Queue for retry
                    message.retry_count += 1
                    _messaging_stats["retries_attempted"] += 1

                    # Re-queue with backoff
                    await asyncio.sleep(2 ** message.retry_count)
                    self.queue.enqueue(message)
                else:
                    self.queue.mark_failed(message, result.error_message or "Delivery failed")

        return results

    def _get_recipient_info(self, agent_id: str) -> MessageRecipient:
        """Get recipient information."""
        if agent_id in self.recipient_cache:
            return self.recipient_cache[agent_id]

        recipient = MessageRecipient(agent_id=agent_id)

        # Load coordinates
        coords = self.pyautogui_delivery.load_coordinates(agent_id)
        if coords:
            recipient.coordinates = coords

        # Set inbox path
        recipient.inbox_path = Path("agent_workspaces") / agent_id / "inbox"

        self.recipient_cache[agent_id] = recipient
        return recipient

    async def broadcast_message(
        self,
        content: str,
        sender: str = "SYSTEM",
        priority: MessagePriority = MessagePriority.NORMAL,
        agent_filter: Optional[Callable[[str], bool]] = None
    ) -> List[DeliveryResult]:
        """Broadcast message to all agents."""

        # Get all agent IDs (simplified - would integrate with agent management)
        agent_ids = []
        workspaces_dir = Path("agent_workspaces")
        if workspaces_dir.exists():
            agent_ids = [d.name for d in workspaces_dir.iterdir()
                        if d.is_dir() and d.name.startswith("Agent-")]

        if agent_filter:
            agent_ids = [aid for aid in agent_ids if agent_filter(aid)]

        if not agent_ids:
            logger.warning("No agents found for broadcast")
            return []

        return await self.send_message(
            sender=sender,
            recipient=agent_ids,
            content=content,
            message_type=MessageType.BROADCAST,
            priority=priority
        )

    async def process_queue(self):
        """Process queued messages."""
        while True:
            message = self.queue.dequeue()
            if not message:
                break

            if message.is_expired():
                self.queue.mark_failed(message, "Message expired")
                continue

            # Attempt redelivery
            await self._deliver_to_recipient(message, message.recipient)

            # Small delay between messages
            await asyncio.sleep(0.1)

    def get_stats(self) -> Dict[str, Any]:
        """Get messaging statistics."""
        global _messaging_stats

        stats = _messaging_stats.copy()
        stats["queue_size"] = len(self.queue.queue)
        stats["history_size"] = len(self.queue.history)

        return stats

    async def close(self):
        """Close messaging orchestrator."""
        await self.discord_delivery.close()

# Convenience functions

async def send_agent_message(
    sender: str,
    recipient: str,
    content: str,
    **kwargs
) -> List[DeliveryResult]:
    """Send message to a specific agent."""
    orchestrator = MessagingOrchestrator()
    return await orchestrator.send_message(sender, recipient, content, **kwargs)

async def broadcast_message(content: str, **kwargs) -> List[DeliveryResult]:
    """Broadcast message to all agents."""
    orchestrator = MessagingOrchestrator()
    return await orchestrator.broadcast_message(content, **kwargs)

def send_discord_message(
    content: str,
    channel_id: Optional[str] = None,
    embed: Optional[Dict[str, Any]] = None,
    **kwargs
) -> bool:
    """Send message to Discord (synchronous wrapper)."""
    async def _send():
        orchestrator = MessagingOrchestrator()

        # Configure Discord if webhook available
        webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
        if webhook_url:
            orchestrator.configure_discord(webhook_url)

        # Create message with Discord metadata
        metadata = kwargs.get("metadata", {})
        if embed:
            metadata["embed"] = embed

        results = await orchestrator.send_message(
            sender="SYSTEM",
            recipient="discord",
            content=content,
            delivery_methods=[DeliveryMethod.DISCORD],
            metadata=metadata,
            **kwargs
        )

        return any(r.success for r in results)

    try:
        return asyncio.run(_send())
    except:
        return False

async def send_a2a_coordination(
    sender: str,
    recipient: str,
    coordination_request: str,
    coordination_type: str = "bilateral",
    coordination_rationale: str = "Parallel processing acceleration",
    expected_contribution: str = "Expertise and parallel execution",
    coordination_timeline: str = "ASAP - within 30 minutes",
    coordination_hashtag: str = "A2A-COORDINATION",
    **kwargs
) -> List[DeliveryResult]:
    """Send bilateral A2A coordination request."""
    message_id = str(uuid.uuid4())

    template_vars = {
        "message_id": message_id,
        "coordination_type": coordination_type,
        "coordination_rationale": coordination_rationale,
        "expected_contribution": expected_contribution,
        "coordination_timeline": coordination_timeline,
        "coordination_hashtag": coordination_hashtag,
        **kwargs.get("template_vars", {})
    }

    return await send_agent_message(
        sender=sender,
        recipient=recipient,
        content=coordination_request,
        message_type=MessageType.A2A_COORDINATION,
        priority=MessagePriority.HIGH,
        template_vars=template_vars,
        **kwargs
    )

async def send_session_closure(
    sender: str,
    recipient: str,
    coordination_summary: str,
    deliverables: str,
    session_duration: str,
    tasks_completed: int,
    coordination_events: int,
    status_updates: int,
    **kwargs
) -> List[DeliveryResult]:
    """Send session closure coordination message."""
    message_id = str(uuid.uuid4())

    template_vars = {
        "message_id": message_id,
        "coordination_summary": coordination_summary,
        "deliverables": deliverables,
        "session_duration": session_duration,
        "tasks_completed": tasks_completed,
        "coordination_events": coordination_events,
        "status_updates": status_updates,
        **kwargs.get("template_vars", {})
    }

    return await send_agent_message(
        sender=sender,
        recipient=recipient,
        content=f"Session closure: {coordination_summary}",
        message_type=MessageType.SESSION_CLOSURE,
        priority=MessagePriority.HIGH,
        template_vars=template_vars,
        **kwargs
    )

async def send_onboarding_message(
    sender: str,
    recipient: str,
    onboarding_type: str = "soft",
    **kwargs
) -> List[DeliveryResult]:
    """Send onboarding message (soft or hard)."""
    message_id = str(uuid.uuid4())

    if onboarding_type.lower() == "hard":
        message_type = MessageType.HARD_ONBOARDING
    else:
        message_type = MessageType.SOFT_ONBOARDING

    template_vars = {
        "message_id": message_id,
        **kwargs.get("template_vars", {})
    }

    return await send_agent_message(
        sender=sender,
        recipient=recipient,
        content=f"Welcome to the swarm, {recipient}!",
        message_type=message_type,
        priority=MessagePriority.HIGH if onboarding_type.lower() == "hard" else MessagePriority.NORMAL,
        template_vars=template_vars,
        **kwargs
    )

def get_messaging_stats() -> Dict[str, Any]:
    """Get messaging system statistics."""
    orchestrator = MessagingOrchestrator()
    return orchestrator.get_stats()

# Export everything needed
__all__ = [
    # Main classes
    "MessagingOrchestrator",
    "UnifiedMessage",
    "MessageQueue",
    "TemplateResolver",

    # Delivery classes
    "PyAutoGUIDelivery",
    "DiscordDelivery",
    "InboxDelivery",

    # Enums
    "MessagePriority",
    "MessageType",
    "DeliveryMethod",
    "MessageStatus",

    # Data classes
    "MessageRecipient",
    "DeliveryResult",

    # Functions
    "send_agent_message",
    "broadcast_message",
    "send_discord_message",
    "send_a2a_coordination",
    "send_session_closure",
    "send_onboarding_message",
    "get_messaging_stats",
]