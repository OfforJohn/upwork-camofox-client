"""Event emission and handling for domain events."""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
import json
import uuid


class EventType(str, Enum):
    """Event type enumeration."""
    JOB_FOUND = "job_found"
    JOB_UPDATED = "job_updated"
    SEARCH_STARTED = "search_started"
    SEARCH_COMPLETE = "search_complete"
    SEARCH_FAILED = "search_failed"
    SESSION_LAUNCHED = "session_launched"
    SESSION_CLOSED = "session_closed"
    SESSION_FAILED = "session_failed"


@dataclass
class Event:
    """Domain event envelope."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: EventType = EventType.JOB_FOUND
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None
    source: str = "upwork-camofox-client"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        return cls(
            id=data["id"],
            type=EventType(data["type"]),
            data=data["data"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            correlation_id=data.get("correlation_id"),
            source=data.get("source", "upwork-camofox-client"),
        )


class EventEmitter:
    """Emits domain events."""

    def __init__(self):
        self.handlers: Dict[EventType, List[callable]] = {}
        self.event_history: List[Event] = []

    def emit(self, event: Event) -> None:
        """Emit an event to registered handlers."""
        self.event_history.append(event)
        
        if event.type in self.handlers:
            for handler in self.handlers[event.type]:
                try:
                    handler(event)
                except Exception as e:
                    print(f"Event handler error: {e}")

    def on(self, event_type: EventType, handler: callable) -> None:
        """Register a handler for an event type."""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)

    def create_job_found_event(self, job_record: Dict[str, Any], correlation_id: Optional[str] = None) -> Event:
        """Create a JobFound event."""
        return Event(
            type=EventType.JOB_FOUND,
            data={"job": job_record},
            correlation_id=correlation_id,
        )

    def create_search_complete_event(self, search_id: str, results_count: int, correlation_id: Optional[str] = None) -> Event:
        """Create a SearchComplete event."""
        return Event(
            type=EventType.SEARCH_COMPLETE,
            data={
                "search_id": search_id,
                "results_count": results_count,
            },
            correlation_id=correlation_id,
        )

    def create_search_failed_event(self, search_id: str, error: str, correlation_id: Optional[str] = None) -> Event:
        """Create a SearchFailed event."""
        return Event(
            type=EventType.SEARCH_FAILED,
            data={
                "search_id": search_id,
                "error": error,
            },
            correlation_id=correlation_id,
        )

    def get_history(self, event_type: Optional[EventType] = None) -> List[Event]:
        """Get event history, optionally filtered by type."""
        if event_type:
            return [e for e in self.event_history if e.type == event_type]
        return self.event_history
