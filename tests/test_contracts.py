"""Test contract fixtures for strict Pydantic validation."""

import json
from pathlib import Path
import pytest
from packages.domain_jobs.summary_parser import JobSummary
from packages.domain_jobs.detail_parser import JobDetail
from packages.domain_records.models import JobRecord
from packages.domain_jobs.search import verify_enrichment_match


def test_accepted_job_summary_validates():
    """Test that accepted_job_summary.json validates with JobSummary model."""
    fixture_path = Path(__file__).parent / "fixtures" / "contracts" / "accepted_job_summary.json"
    with open(fixture_path, encoding='utf-8') as f:
        data = json.load(f)
    
    summary = JobSummary(**data)
    assert summary.job_id == "2090361778369164301"
    assert summary.title == "Quant / Python Developer for AI Trading Bot"
    assert summary.url.startswith("https://www.upwork.com")
    assert "Python" in summary.tags


def test_accepted_job_detail_validates():
    """Test that accepted_job_detail.json validates with JobDetail model."""
    fixture_path = Path(__file__).parent / "fixtures" / "contracts" / "accepted_job_detail.json"
    with open(fixture_path, encoding='utf-8') as f:
        data = json.load(f)
    
    detail = JobDetail(**data)
    assert detail.job_id == "2090361778369164301"
    assert detail.title == "Quant / Python Developer for AI Trading Bot"
    assert detail.status == "open"


def test_rejected_job_records():
    """Test that rejected_job_records.json cases fail with expected errors."""
    fixture_path = Path(__file__).parent / "fixtures" / "contracts" / "rejected_job_records.json"
    with open(fixture_path, encoding='utf-8') as f:
        data = json.load(f)
    
    for rejection in data["rejections"]:
        case = rejection["case"]
        expected_error = rejection["expected_error"]
        
        if case == "summary_detail_id_mismatch":
            # Test enrichment verification
            summary_data = rejection["summary"]
            detail_data = rejection["detail"]
            
            summary = JobSummary(**summary_data)
            detail = JobDetail(**detail_data)
            
            with pytest.raises(Exception) as exc_info:
                verify_enrichment_match(summary, detail)
            
            assert expected_error in str(exc_info.value)
        
        elif case == "fabricated_unknown_date":
            # Test JobSummary validation
            summary_data = rejection["data"]
            
            with pytest.raises(Exception) as exc_info:
                JobSummary(**summary_data)
            
            assert expected_error in str(exc_info.value)
        
        else:
            # Test JobRecord validation
            record_data = rejection["data"]
            
            with pytest.raises(Exception) as exc_info:
                JobRecord(**record_data)
            
            assert expected_error in str(exc_info.value)


def test_accepted_summary_serialization():
    """Test that accepted summary can be serialized to JSON."""
    fixture_path = Path(__file__).parent / "fixtures" / "contracts" / "accepted_job_summary.json"
    with open(fixture_path, encoding='utf-8') as f:
        data = json.load(f)
    
    summary = JobSummary(**data)
    serialized = summary.model_dump_json(indent=2)
    
    # Verify it's valid JSON
    parsed_back = json.loads(serialized)
    assert parsed_back["job_id"] == data["job_id"]


def test_accepted_detail_serialization():
    """Test that accepted detail can be serialized to JSON."""
    fixture_path = Path(__file__).parent / "fixtures" / "contracts" / "accepted_job_detail.json"
    with open(fixture_path, encoding='utf-8') as f:
        data = json.load(f)
    
    detail = JobDetail(**data)
    serialized = detail.model_dump_json(indent=2)
    
    # Verify it's valid JSON
    parsed_back = json.loads(serialized)
    assert parsed_back["job_id"] == data["job_id"]


def test_enrichment_verification_passes():
    """Test that enrichment verification passes with matching IDs."""
    summary = JobSummary(
        job_id="12345",
        title="Test Job",
        url="https://www.upwork.com/jobs/test",
        description="Test description",
        posted_date="Posted 2 hours ago"
    )
    
    detail = JobDetail(
        job_id="12345",
        title="Test Job",
        url="https://www.upwork.com/jobs/test",
        description="Test description",
        posted_date="Posted 2 hours ago"
    )
    
    # Should not raise
    assert verify_enrichment_match(summary, detail) is True


def test_enrichment_verification_fails_id_mismatch():
    """Test that enrichment verification fails with ID mismatch."""
    summary = JobSummary(
        job_id="12345",
        title="Test Job",
        url="https://www.upwork.com/jobs/test",
        description="Test description",
        posted_date="Posted 2 hours ago"
    )
    
    detail = JobDetail(
        job_id="67890",
        title="Test Job",
        url="https://www.upwork.com/jobs/test",
        description="Test description",
        posted_date="Posted 2 hours ago"
    )
    
    with pytest.raises(Exception) as exc_info:
        verify_enrichment_match(summary, detail)
    
    assert "Job ID mismatch" in str(exc_info.value)
