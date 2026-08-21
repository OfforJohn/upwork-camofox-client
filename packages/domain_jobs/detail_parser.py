"""
Job detail parser using selectolax for HTML parsing and Pydantic for validation.
Input: Full job detail page HTML
Output: Validated JobDetail
"""

from selectolax.parser import HTMLParser
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import List, Optional
from datetime import datetime
from .models import Budget


class JobDetail(BaseModel):
    """Validated job detail extracted from a job detail page."""
    
    model_config = ConfigDict(extra="forbid")
    
    job_id: str = Field(..., description="Unique job ID")
    title: str = Field(..., description="Job title")
    description: str = Field(..., description="Full job description")
    url: Optional[str] = Field(None, description="Job URL (set from navigation context)")
    client_id: Optional[str] = Field(None, description="Client ID")
    client_name: Optional[str] = Field(None, description="Client name")
    posted_date: str = Field(..., description="Posted date text")
    posted_at: Optional[datetime] = Field(None, description="Absolute posting timestamp")
    budget: Optional[Budget] = Field(None, description="Budget information")
    tags: List[str] = Field(default_factory=list, description="Job tags/skills")
    status: str = Field(default="open", description="Job status")
    proposal_count: Optional[int] = Field(None, description="Number of proposals")
    interview_stage: Optional[str] = Field(None, description="Interview stage")
    activity_date: Optional[str] = Field(None, description="Last activity date")
    
    @field_validator('job_id')
    @classmethod
    def validate_job_id(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("job_id is required and cannot be empty")
        return v.strip()
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("title is required and cannot be empty")
        return v.strip()
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("description is required and cannot be empty")
        return v.strip()
    
    @field_validator('posted_date')
    @classmethod
    def validate_posted_date(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("posted_date is required and cannot be empty")
        if v == "Unknown":
            raise ValueError("posted_date cannot be 'Unknown'")
        return v.strip()


def parse_detail_page(html: str) -> JobDetail:
    """
    Parse a job detail page HTML and return validated JobDetail.
    
    Args:
        html: The full HTML of a job detail page
        
    Returns:
        JobDetail: Validated job detail
        
    Raises:
        ValueError: If required fields are missing or invalid
    """
    parser = HTMLParser(html)
    
    # Extract job ID from URL or data attributes
    job_id = None
    
    # Try to find job ID in data attributes
    job_id_element = parser.css_first('[data-ev-job-uid]')
    if job_id_element:
        job_id = job_id_element.attrs.get('data-ev-job-uid')
    
    if not job_id:
        raise ValueError("Missing job_id in detail page")
    
    # Extract title
    title_element = parser.css_first('[data-test="job-title"], h1, h2')
    if not title_element:
        raise ValueError("Missing job title element")
    
    title = title_element.text(strip=True)
    
    # Extract description
    desc_element = parser.css_first('[data-test="job-description"], .job-description')
    if not desc_element:
        raise ValueError("Missing job description element")
    
    description = desc_element.text(strip=True)
    
    # Extract URL from canonical link or current page
    url_element = parser.css_first('link[rel="canonical"]')
    if url_element:
        url = url_element.attrs.get('href', '')
    else:
        url = ""  # Will be set from navigation context
    
    # Extract posted date
    posted_element = parser.css_first('[data-test="job-published-date"], .job-published-date')
    if not posted_element:
        raise ValueError("Missing posted date element")
    posted_date = posted_element.text(strip=True)
    if not posted_date:
        raise ValueError("Empty posted date")
    
    # Extract client information
    client_id = None
    client_name = None
    
    client_element = parser.css_first('[data-test="client-name"], .client-name')
    if client_element:
        client_name = client_element.text(strip=True)
    
    client_id_element = parser.css_first('[data-client-uid]')
    if client_id_element:
        client_id = client_id_element.attrs.get('data-client-uid')
    
    # Extract tags
    tags = list(dict.fromkeys(
        tag.text(strip=True)
        for tag in parser.css('[data-test="skill"], [data-test="token"], .skill-tag')
        if tag.text(strip=True)
    ))
    
    # Extract budget info
    budget_dict = {}
    budget_element = parser.css_first('[data-test="job-budget"], .job-budget')
    if budget_element:
        budget_dict['text'] = budget_element.text(strip=True)
    
    # Extract proposal count
    proposal_element = parser.css_first('[data-test="proposal-count"], .proposal-count')
    if proposal_element:
        proposal_text = proposal_element.text(strip=True)
        try:
            proposal_count = int(''.join(filter(str.isdigit, proposal_text)))
            budget_dict['proposals'] = proposal_count
        except ValueError:
            pass
    
    # Convert to Budget model if we have data
    budget_obj = Budget(**budget_dict) if budget_dict else None
    
    return JobDetail(
        job_id=job_id,
        title=title,
        description=description,
        url=url,
        client_id=client_id,
        client_name=client_name,
        posted_date=posted_date,
        posted_at=None,  # Parse absolute timestamp if available
        budget=budget_obj,
        tags=tags,
        status="open",
        proposal_count=budget_obj.proposals if budget_obj else None,
    )
