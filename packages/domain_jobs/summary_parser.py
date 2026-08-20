"""
Job summary parser using selectolax for HTML parsing and Pydantic for validation.
Input: Single job card's outerHTML
Output: Validated JobSummary
"""

from selectolax.parser import HTMLParser
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
import re


class JobSummary(BaseModel):
    """Validated job summary extracted from a single job card HTML."""
    
    job_id: str = Field(..., description="Unique job ID from data-ev-job-uid attribute")
    title: str = Field(..., description="Job title")
    url: str = Field(..., description="Job URL")
    description: str = Field(..., description="Job description")
    posted_date: str = Field(..., description="Posted date text")
    client_id: Optional[str] = Field(None, description="Client ID")
    client_name: Optional[str] = Field(None, description="Client name")
    tags: List[str] = Field(default_factory=list, description="Job tags/skills")
    budget: Dict[str, Any] = Field(default_factory=dict, description="Budget information")
    
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
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("url is required and cannot be empty")
        if not v.startswith('/'):
            raise ValueError("url must start with /")
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
        return v.strip()


def parse_summary_card(html: str) -> JobSummary:
    """
    Parse a single job card HTML and return validated JobSummary.
    
    Args:
        html: The outerHTML of a single job card
        
    Returns:
        JobSummary: Validated job summary
        
    Raises:
        ValueError: If required fields are missing or invalid
    """
    parser = HTMLParser(html)
    
    # Extract job ID from data-ev-job-uid attribute (may be on card or child element)
    job_card = parser.root
    job_id = job_card.attrs.get('data-ev-job-uid')
    if not job_id:
        # Try to find it on child elements
        job_id_element = job_card.css_first('[data-ev-job-uid]')
        if job_id_element:
            job_id = job_id_element.attrs.get('data-ev-job-uid')
    
    if not job_id:
        raise ValueError("Missing data-ev-job-uid attribute on job card")
    
    # Extract title and URL from job-tile-title-link or fallback to any link in job-tile-title
    title_link = job_card.css_first('[data-test="job-tile-title-link"]')
    if not title_link:
        # Fallback: find any link within job-tile-title or h2/h3 with class job-tile-title
        title_link = job_card.css_first('.job-tile-title a, h2.job-tile-title a, h3.job-tile-title a')
        if not title_link:
            # Last resort: find any link with /jobs/ in href
            all_links = job_card.css('a')
            for link in all_links:
                href = link.attrs.get('href', '')
                if '/jobs/' in href:
                    title_link = link
                    break
        
        if not title_link:
            raise ValueError("Missing job title link element")
    
    title = title_link.text(strip=True)
    url = title_link.attrs.get('href')
    if not url:
        raise ValueError("Missing href attribute on job title link")
    
    # Extract description from JobDescription
    desc_element = job_card.css_first('[data-test="UpCLineClamp JobDescription"]')
    if not desc_element:
        raise ValueError("Missing JobDescription element")
    
    description = desc_element.text(strip=True)
    if not description:
        raise ValueError("Empty job description")
    
    # Extract posted date from job-pubilshed-date
    posted_element = job_card.css_first('[data-test="job-pubilshed-date"]')
    if not posted_element:
        raise ValueError("Missing job-pubilshed-date element")
    
    posted_date = posted_element.text(strip=True)
    if not posted_date:
        raise ValueError("Empty posted date")
    
    # Extract client info - look for client information in the card
    client_id = job_id  # Use job_id as client_id fallback (same attribute)
    client_name = None
    
    # Try to find client name from various possible selectors
    client_element = job_card.css_first('[data-test="client-name"]')
    if not client_element:
        # Try alternative selectors for client information
        client_element = job_card.css_first('[data-test="JobInfoClient"]')
    
    if client_element:
        # Extract just the client name, not the entire section
        # The client name is typically in a span or strong tag
        name_element = client_element.css_first('span, strong')
        if name_element:
            text = name_element.text(strip=True)
            # Filter out non-name content like "Unverified", "Payment", "Rating", etc.
            if text and len(text) < 50 and not any(word in text.lower() for word in ['unverified', 'payment', 'rating', 'feedback', 'spent', 'location']):
                client_name = text
    
    # If still no client name, leave it as None (no fallback)
    
    # Extract tags
    tags = []
    tag_elements = job_card.css('[data-test="token"]')
    for tag_element in tag_elements:
        tag_text = tag_element.text(strip=True)
        if tag_text:
            tags.append(tag_text)
    
    # Extract budget info
    budget = {}
    job_info = job_card.css_first('[data-test="JobInfo"]')
    if job_info:
        # Extract job type/budget
        job_type = job_info.css_first('[data-test="job-type-label"]')
        if job_type:
            budget['job_type'] = job_type.text(strip=True)
        
        # Extract proposals
        proposals = job_card.css_first('[data-test="proposals-tier"]')
        if proposals:
            budget['proposals'] = proposals.text(strip=True)
    
    return JobSummary(
        job_id=job_id,
        title=title,
        url=url,
        description=description,
        posted_date=posted_date,
        client_id=client_id,
        client_name=client_name,
        tags=tags,
        budget=budget
    )
