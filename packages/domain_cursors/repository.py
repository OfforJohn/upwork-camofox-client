"""Cursor repository for managing pagination cursors."""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime, UTC
import uuid


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


class CursorRepository:
    """Repository for cursor persistence and management."""

    def __init__(self):
        self._storage: Dict[str, CursorRecord] = {}  # In-memory for demo

    async def save(self, cursor: CursorRecord) -> None:
        """Save cursor to storage."""
        cursor.updated_at = datetime.now(UTC)
        self._storage[cursor.id] = cursor

    async def get(self, cursor_id: str) -> Optional[CursorRecord]:
        """Get cursor by ID."""
        return self._storage.get(cursor_id)

    async def get_by_search(self, search_id: str) -> Optional[CursorRecord]:
        """Get latest cursor for a search."""
        for cursor in reversed(list(self._storage.values())):
            if cursor.search_id == search_id:
                return cursor
        return None

    async def delete(self, cursor_id: str) -> None:
        """Delete cursor by ID."""
        if cursor_id in self._storage:
            del self._storage[cursor_id]

    async def list_all(self) -> list[CursorRecord]:
        """List all cursors."""
        return list(self._storage.values())
