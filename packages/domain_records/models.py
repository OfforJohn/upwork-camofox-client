"""Data models for normalized records and cursors."""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime, UTC
from enum import Enum
import uuid


class JobStatus(str, Enum):
    """Job status enumeration."""
    OPEN = "open"
    CLOSED = "closed"
    FILLED = "filled"
    EXPIRED = "expired"


@dataclass
class JobRecord:
    """Normalized job record."""
    id: str
    title: str
    description: str
    client_id: str
    client_name: str
    posted_date: datetime
    url: str
    status: JobStatus = JobStatus.OPEN
    budget: Optional[Dict[str, Any]] = None
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.id,
            "title": self.title,
            "description": self.description,
            "client_id": self.client_id,
            "client_name": self.client_name,
            "posted_date": self.posted_date.isoformat(),
            "url": self.url,
            "status": self.status.value,
            "budget": self.budget,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JobRecord":
        return cls(
            id=data.get("job_id", data.get("id")),
            title=data["title"],
            description=data["description"],
            client_id=data["client_id"],
            client_name=data["client_name"],
            posted_date=datetime.fromisoformat(data["posted_date"]),
            url=data["url"],
            status=JobStatus(data.get("status", "open")),
            budget=data.get("budget"),
            tags=data.get("tags", []),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )


@dataclass
class CursorRecord:
    """Cursor record for tracking pagination position."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    search_id: str = ""
    position: int = 0
    total_results: int = 0
    next_page_token: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "search_id": self.search_id,
            "position": self.position,
            "total_results": self.total_results,
            "next_page_token": self.next_page_token,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CursorRecord":
        return cls(
            id=data["id"],
            search_id=data["search_id"],
            position=data["position"],
            total_results=data["total_results"],
            next_page_token=data.get("next_page_token"),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )

    def advance(self, step: int = 1) -> None:
        """Advance cursor position."""
        self.position += step
        self.updated_at = datetime.now(UTC)

    def reset(self) -> None:
        """Reset cursor to initial position."""
        self.position = 0
        self.next_page_token = None
        self.updated_at = datetime.now(UTC)
