"""Shared Pydantic models for job data."""

from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional, Union
from urllib.parse import urlparse


def validate_upwork_url(v: str) -> str:
    """Validate that a URL is a valid Upwork job URL.
    
    Args:
        v: The URL string to validate
        
    Returns:
        The validated URL string
        
    Raises:
        ValueError: If URL is invalid or not a proper Upwork job URL
    """
    if not v or v.strip() == "":
        raise ValueError("url is required and cannot be empty")
    
    parsed = urlparse(v.strip())
    
    if parsed.scheme != "https":
        raise ValueError("url must use https scheme")
    
    if parsed.netloc != "www.upwork.com":
        raise ValueError("url must be a valid Upwork URL")
    
    if "/jobs/" not in parsed.path:
        raise ValueError("url must contain /jobs/ path")
    
    return v.strip()


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
