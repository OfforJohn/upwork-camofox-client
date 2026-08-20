"""Tests for ActionRunner covering auth failure, record-save failure, and cursor-save ordering."""

import pytest
from datetime import datetime
from packages.domain_actions.runner import ActionRunner, ActionEnvelope, ActionType
from packages.domain_camofox.session import SessionManager, SessionConfig
from packages.domain_camofox.interface import FakeBrowser
from packages.domain_accounts.auth_guard import AuthGuard, AuthValidationResult
from packages.domain_cursors.repository import CursorRepository
from packages.domain_jobs.search import JobsSearch, JobSearchParams, UpworkBlockedError


class TestAuthFailure:
    """Test authentication failure scenarios."""

    @pytest.mark.asyncio
    async def test_auth_validation_failure_returns_error(self):
        """Test that auth validation failure returns error result."""
        # Create runner with fake browser that simulates login page
        class LoginFakeBrowser(FakeBrowser):
            async def navigate(self, url: str) -> None:
                await super().navigate(url)
                # Override to simulate login page URL
                self._current_url = "https://www.upwork.com/ab/account-security/login"

        browser_factory = lambda config: LoginFakeBrowser()
        runner = ActionRunner()
        runner.session_manager = SessionManager(browser_factory=browser_factory)

        # Create action envelope
        action = ActionEnvelope(
            type=ActionType.JOBS_SEARCH,
            account_id="test_account",
            payload={"query": "python"},
        )

        # Execute action
        result = await runner.execute(action)

        # Assert auth failure
        assert not result.success
        assert "Authentication validation failed" in result.error


class TestRecordSaveFailure:
    """Test record save failure scenarios."""

    @pytest.mark.asyncio
    async def test_record_save_failure_prevents_cursor_advance(self):
        """Test that record save failure prevents cursor advance."""
        from pathlib import Path

        # Load fixture HTML for real parsed records
        fixture_path = Path(__file__).parent.parent / "tests" / "fixtures" / "upwork_job_listing.html"
        html = fixture_path.read_text(encoding="utf-8")

        # Create fake browser that simulates login page
        browser_factory = lambda config: FakeBrowser(should_authenticate=False, page_content=html)
        runner = ActionRunner()
        runner.session_manager = SessionManager(browser_factory=browser_factory)

        # Create failing job repository that raises on first save
        class FailingJobRepository(dict):
            def __init__(self):
                super().__init__()
                self.saved = []

            def __setitem__(self, key, value):
                self.saved.append(value)
                raise RuntimeError("record save failed")

        runner.job_storage = FailingJobRepository()

        # Create action envelope
        action = ActionEnvelope(
            type=ActionType.JOBS_SEARCH,
            account_id="test_account",
            payload={"query": "python"},
        )

        # Execute action - should raise RuntimeError on record save
        with pytest.raises(RuntimeError, match="record save failed"):
            await runner.execute(action)

        # Assert cursor was not saved due to record save failure
        cursor = await runner.cursor_repository.get("test_account")
        assert cursor is None


class TestCursorSaveOrdering:
    """Test cursor save ordering invariant."""

    @pytest.mark.asyncio
    async def test_records_saved_before_cursor(self):
        """Test that records are saved before cursor is advanced."""
        # Create runner with fake browser (returns fixture HTML, so records are created)
        browser_factory = lambda config: FakeBrowser(should_authenticate=True)
        runner = ActionRunner()
        runner.session_manager = SessionManager(browser_factory=browser_factory)

        # Track save order
        save_order = []

        original_cursor_repo = runner.cursor_repository

        class TrackingCursorRepository(CursorRepository):
            async def save(self, cursor):
                save_order.append("cursor")
                await super().save(cursor)

        runner.cursor_repository = TrackingCursorRepository()

        # Track record saves
        original_job_storage = runner.job_storage

        class TrackingStorage(dict):
            def __setitem__(self, key, value):
                save_order.append("record")
                super().__setitem__(key, value)

        runner.job_storage = TrackingStorage()

        # Create action envelope
        action = ActionEnvelope(
            type=ActionType.JOBS_SEARCH,
            account_id="test_account",
            payload={"query": "python"},
        )

        # Execute action
        result = await runner.execute(action)

        # Assert exact event order: record, record, cursor
        assert len(save_order) == 3, f"Expected 3 save events (2 records + 1 cursor), got {len(save_order)}"
        assert save_order == ["record", "record", "cursor"], f"Expected [record, record, cursor], got {save_order}"


class TestIntegration:
    """Integration tests for full runner flow."""

    @pytest.mark.asyncio
    async def test_successful_search_flow(self):
        """Test successful search flow with all components."""
        # Create runner with fake browser
        browser_factory = lambda config: FakeBrowser(should_authenticate=True)
        runner = ActionRunner()
        runner.session_manager = SessionManager(browser_factory=browser_factory)

        # Create action envelope
        action = ActionEnvelope(
            type=ActionType.JOBS_SEARCH,
            account_id="test_account",
            payload={"query": "python"},
        )

        # Execute action
        result = await runner.execute(action)

        # Assert success
        assert result.success
        assert result.data is not None
        assert "search_id" in result.data
        assert "cursor_id" in result.data

    @pytest.mark.asyncio
    async def test_fixture_extraction_produces_two_listings(self):
        """Test that fixture extraction produces exactly 2 job listings."""
        # Skip this test for now - DOM extraction requires real Playwright page object
        pytest.skip("DOM extraction requires real Playwright page object, not FakeBrowser")


class TestJobsSearchURL:
    """Test JobsSearch URL construction."""

    def test_build_search_url_includes_query_filter(self):
        """Test that _build_search_url includes query parameter in URL."""
        fake_browser = FakeBrowser()
        jobs_search = JobsSearch(fake_browser)

        params = JobSearchParams(query="python")
        url = jobs_search._build_search_url(params)

        assert "q=python" in url
        assert "https://www.upwork.com/nx/search/jobs/" in url

    def test_build_search_url_without_query(self):
        """Test that _build_search_url returns base URL when no query."""
        fake_browser = FakeBrowser()
        jobs_search = JobsSearch(fake_browser)

        params = JobSearchParams()
        url = jobs_search._build_search_url(params)

        assert url == "https://www.upwork.com/nx/search/jobs/"


class TestPageStateGuard:
    """Test page state guard for Cloudflare challenge detection."""

    def test_cloudflare_challenge_raises_blocked_error(self):
        """Test that Cloudflare challenge page raises UpworkBlockedError."""
        fake_browser = FakeBrowser()
        jobs_search = JobsSearch(fake_browser)

        # Cloudflare challenge HTML
        challenge_html = "<html><title>Just a moment...</title></html>"

        with pytest.raises(UpworkBlockedError, match="Cloudflare challenge"):
            jobs_search._assert_search_page(challenge_html)

    def test_cf_chl_marker_raises_blocked_error(self):
        """Test that cf-chl- marker raises UpworkBlockedError."""
        fake_browser = FakeBrowser()
        jobs_search = JobsSearch(fake_browser)

        # HTML with cf-chl- marker
        challenge_html = "<html><div class='cf-chl-opt'></div></html>"

        with pytest.raises(UpworkBlockedError, match="Cloudflare challenge"):
            jobs_search._assert_search_page(challenge_html)

    def test_valid_search_page_passes_guard(self):
        """Test that valid search page passes guard without error."""
        fake_browser = FakeBrowser()
        jobs_search = JobsSearch(fake_browser)

        # Valid search page HTML
        valid_html = "<html><title>Upwork Job Search</title></html>"

        # Should not raise
        jobs_search._assert_search_page(valid_html)

    def test_valid_page_with_zero_listings_returns_empty_list(self):
        """Test that valid page with no job listings returns empty list."""
        # Skip this test for now - DOM extraction requires real Playwright page object
        pytest.skip("DOM extraction requires real Playwright page object, not FakeBrowser")
