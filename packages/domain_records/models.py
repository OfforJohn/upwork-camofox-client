"""Data models for normalized records and cursors."""

from pydantic import BaseModel, ConfigDict, field_validator, Field
from typing import Optional, Dict, Any, List
from datetime import datetime, UTC
from enum import Enum
import uuid
from packages.domain_jobs.models import Budget


class JobStatus(str, Enum):
    """Job status enumeration."""
    OPEN = "open"
    CLOSED = "closed"
    FILLED = "filled"
    EXPIRED = "expired"


class JobRecord(BaseModel):
    """Normalized job record."""
    
    model_config = ConfigDict(extra="forbid")
    
    id: str
    title: str
    description: str
    url: str
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    posted_date: Optional[datetime] = None
    posted_date_text: Optional[str] = None
    status: JobStatus = JobStatus.OPEN
    budget: Optional[Budget] = None
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    
    @field_validator('id')
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("id is required and cannot be empty")
        return v.strip()
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("url is required and cannot be empty")
        if not v.startswith("https://www.upwork.com"):
            raise ValueError("url must be a valid Upwork URL")
        return v.strip()
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("description is required and cannot be empty")
        return v.strip()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.id,
            "title": self.title,
            "description": self.description,
            "client_id": self.client_id,
            "client_name": self.client_name,
            "posted_date": self.posted_date.isoformat() if self.posted_date else None,
            "posted_date_text": self.posted_date_text,
            "url": self.url,
            "status": self.status.value,
            "budget": self.budget.model_dump() if self.budget else None,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JobRecord":
        posted_raw = data.get("posted_date")
        created_raw = data.get("created_at")
        updated_raw = data.get("updated_at")
        budget_raw = data.get("budget")

        return cls(
            id=data.get("job_id") or data.get("id"),
            title=data.get("title"),
            description=data.get("description"),
            client_id=data.get("client_id"),
            client_name=data.get("client_name"),
            posted_date=(
                datetime.fromisoformat(posted_raw)
                if isinstance(posted_raw, str) and posted_raw
                else posted_raw
            ),
            posted_date_text=data.get("posted_date_text"),
            url=data.get("url"),
            status=JobStatus(data.get("status", "open")),
            budget=(
                budget_raw
                if isinstance(budget_raw, Budget)
                else Budget.model_validate(budget_raw)
                if budget_raw is not None
                else None
            ),
            tags=data.get("tags", []),
            created_at=(
                datetime.fromisoformat(created_raw)
                if isinstance(created_raw, str) and created_raw
                else created_raw
            ),
            updated_at=(
                datetime.fromisoformat(updated_raw)
                if isinstance(updated_raw, str) and updated_raw
                else updated_raw
            ),
        )


class CursorRecord(BaseModel):
    """Cursor record for tracking pagination position."""
    
    model_config = ConfigDict(extra="forbid")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    search_id: str = ""
    position: int = 0
    total_results: int = 0
    next_page_token: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

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
