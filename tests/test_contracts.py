"""Test contract fixtures for strict Pydantic validation."""

import json
from pathlib import Path
import pytest
from packages.domain_jobs.summary_parser import JobSummary
from packages.domain_jobs.detail_parser import JobDetail
from packages.domain_records.models import JobRecord
from packages.domain_jobs.search import verify_enrichment_match
from datetime import datetime, UTC


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


def test_job_record_from_dict_missing_optional_client_keys():
    """Test that JobRecord.from_dict() handles missing optional client keys."""
    data = {
        "job_id": "12345",
        "title": "Test Job",
        "description": "Test description",
        "url": "https://www.upwork.com/jobs/test",
        "status": "open"
    }
    
    # Should not raise - client_id and client_name are optional
    record = JobRecord.from_dict(data)
    assert record.id == "12345"
    assert record.client_id is None
    assert record.client_name is None


def test_job_record_timestamp_round_trip():
    """Test that timestamps are preserved through to_dict/from_dict round trip."""
    original = JobRecord(
        id="12345",
        title="Test Job",
        description="Test description",
        url="https://www.upwork.com/jobs/test"
    )
    
    # Serialize
    serialized = original.to_dict()
    assert "created_at" in serialized
    assert "updated_at" in serialized
    
    # Deserialize
    deserialized = JobRecord.from_dict(serialized)
    
    # Serialize again
    reserialized = deserialized.to_dict()
    
    # Timestamps should be preserved (not regenerated)
    assert serialized["created_at"] == reserialized["created_at"]
    assert serialized["updated_at"] == reserialized["updated_at"]


def test_job_record_independent_tag_lists():
    """Test that two JobRecord instances don't share the same tag list."""
    record1 = JobRecord(
        id="12345",
        title="Test Job",
        description="Test description",
        url="https://www.upwork.com/jobs/test",
        tags=["Python"]
    )
    
    record2 = JobRecord(
        id="67890",
        title="Another Job",
        description="Another description",
        url="https://www.upwork.com/jobs/test2"
    )
    
    # Modify record1's tags
    record1.tags.append("Django")
    
    # record2's tags should remain empty
    assert len(record2.tags) == 0
    assert "Django" not in record2.tags


def test_lookalike_host_rejection():
    """Test that lookalike hosts like www.upwork.com.evil.example are rejected."""
    with pytest.raises(ValueError) as exc_info:
        JobSummary(
            job_id="12345",
            title="Test Job",
            url="https://www.upwork.com.evil.example/jobs/test/~12345",
            description="Test description",
            posted_date="Posted 2 hours ago"
        )
    
    assert "url must be a valid Upwork URL" in str(exc_info.value)


def test_job_record_lookalike_host_rejection():
    """Test that JobRecord rejects lookalike hosts."""
    with pytest.raises(ValueError) as exc_info:
        JobRecord(
            id="12345",
            title="Test Job",
            description="Test description",
            url="https://www.upwork.com.evil.example/jobs/test/~12345"
        )
    
    assert "url must be a valid Upwork URL" in str(exc_info.value)


def test_missing_canonical_url_validation():
    """Test that JobDetail raises error when canonical URL is missing."""
    from packages.domain_jobs.detail_parser import parse_detail_page
    
    # HTML without canonical link
    html_without_canonical = """
    <html>
    <body>
        <div data-ev-job-uid="12345">
            <h1 data-test="job-title">Test Job</h1>
            <div data-test="job-description">Test description</div>
            <div data-test="job-published-date">Posted 2 hours ago</div>
        </div>
    </body>
    </html>
    """
    
    with pytest.raises(ValueError) as exc_info:
        parse_detail_page(html_without_canonical)
    
    assert "Missing canonical URL" in str(exc_info.value)


def test_canonical_url_mismatch_in_enrichment():
    """Test that enrichment verification fails when canonical URL doesn't match summary."""
    summary = JobSummary(
        job_id="12345",
        title="Test Job",
        url="https://www.upwork.com/jobs/test-job/~12345",
        description="Test description",
        posted_date="Posted 2 hours ago"
    )
    
    # Detail with different canonical URL (different job ID)
    detail = JobDetail(
        job_id="12345",  # Same job ID but different URL
        title="Test Job",
        url="https://www.upwork.com/jobs/other-job/~67890",
        description="Test description",
        posted_date="Posted 2 hours ago"
    )
    
    with pytest.raises(Exception) as exc_info:
        verify_enrichment_match(summary, detail)
    
    assert "URL mismatch" in str(exc_info.value)
