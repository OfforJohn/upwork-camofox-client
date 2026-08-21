"""Shared Pydantic models for job data."""

from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional, Union


class Budget(BaseModel):
    """Typed budget information for job listings."""
    
    model_config = ConfigDict(extra="forbid")
    
    job_type: Optional[str] = None  # e.g., "Fixed price", "Hourly: $19.00 - $40.00"
    proposals: Optional[Union[str, int]] = None  # e.g., "Proposals: 5 to 10" or 5
    text: Optional[str] = None  # Raw budget text from HTML
    
    @field_validator('proposals')
    @classmethod
    def validate_proposals(cls, v):
        if v is not None:
            return str(v) if isinstance(v, int) else v
        return v
