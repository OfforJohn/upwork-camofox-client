"""Action runner for processing action envelopes."""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime, UTC
import json
import uuid
from enum import Enum

from ..domain_camofox.session import SessionManager, SessionConfig, ProxyConfig, HumanizationConfig, Cookie, CamofoxSession
from ..domain_jobs.search import JobsSearch, JobSearchParams
from ..domain_records.models import JobRecord, CursorRecord
from ..domain_records.normalizer import JobNormalizer
from ..domain_events.events import EventEmitter, Event, EventType
from ..domain_accounts.auth_guard import AuthGuard
from ..domain_cursors.repository import CursorRepository


class ActionType(str, Enum):
    """Action type enumeration."""
    JOBS_SEARCH = "jobs.search"
    JOBS_GET = "jobs.get"
    PROPOSALS_DRAFT = "proposals.draft"
    PROPOSALS_SUBMIT = "proposals.submit"


@dataclass
class ActionEnvelope:
    """Action envelope for request processing."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: ActionType = ActionType.JOBS_SEARCH
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    account_id: str = ""
    correlation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "account_id": self.account_id,
            "correlation_id": self.correlation_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActionEnvelope":
        return cls(
            id=data["id"],
            type=ActionType(data["type"]),
            payload=data["payload"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            account_id=data["account_id"],
            correlation_id=data.get("correlation_id"),
        )


@dataclass
class ActionResult:
    """Result of action execution."""
    action_id: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    events: List[Event] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "events": [e.to_dict() for e in self.events],
        }


class ActionRunner:
    """Runs actions through the vertical slice pipeline."""

    def __init__(self):
        self.session_manager = SessionManager()
        self.event_emitter = EventEmitter()
        self.normalizer = JobNormalizer()
        self.job_storage: Dict[str, JobRecord] = {}  # In-memory storage for demo
        self.cursor_repository = CursorRepository()

    async def execute(self, action: ActionEnvelope) -> ActionResult:
        """Execute an action through the pipeline."""
        if action.type == ActionType.JOBS_SEARCH:
            return await self._execute_jobs_search(action)
        elif action.type == ActionType.JOBS_GET:
            return await self._execute_jobs_get(action)
        else:
            return ActionResult(
                action_id=action.id,
                success=False,
                error=f"Unsupported action type: {action.type}",
            )

    async def _execute_jobs_search(self, action: ActionEnvelope) -> ActionResult:
        """Execute jobs.search vertical slice following Facebook client pattern."""
        correlation_id = action.correlation_id or action.id
        
        # Step 1: Get or create Camofox session
        session_config = self._build_session_config(action.account_id)
        session = await self.session_manager.get_session(action.account_id, session_config)
        
        # Emit session launched event
        session_event = Event(
            type=EventType.SESSION_LAUNCHED,
            data={"account_id": action.account_id},
            correlation_id=correlation_id,
        )
        self.event_emitter.emit(session_event)
        
        # Step 2: Open Upwork surface
        await session.navigate("https://www.upwork.com")

        # Step 3: Read title/url for auth validation
        page_info = await session.get_page_info()

        # Step 4: AuthGuard.validate(title, url)
        auth_guard = AuthGuard(session)
        auth_result = await auth_guard.validate(page_info.title, page_info.url)
        
        if not auth_result.is_authenticated:
            return ActionResult(
                action_id=action.id,
                success=False,
                error=f"Authentication validation failed: {auth_result.error}",
            )
        
        # Step 5: Parse search parameters
        search_params = JobSearchParams(**action.payload)
        
        # Step 6: Execute search via Camofox session
        jobs_search = JobsSearch(session)
        listings = await jobs_search.search(search_params)
        
        # Step 7: Normalize job records
        job_records = self.normalizer.normalize_batch(listings)
        
        # Step 8: Deduplicate against existing records
        existing_ids = set(self.job_storage.keys())
        new_records = self.normalizer.deduplicate(job_records, existing_ids)
        
        # Step 9: Save records BEFORE cursor (key invariant)
        search_id = str(uuid.uuid4())
        saved_records = []
        for record in new_records:
            self.job_storage[record.id] = record
            saved_records.append(record)
            
            # Emit job found event
            job_event = self.event_emitter.create_job_found_event(
                job_record=record.to_dict(),
                correlation_id=correlation_id,
            )
            self.event_emitter.emit(job_event)
        
        # Step 10: Advance cursor only after successful record persistence
        cursor = CursorRecord(
            id=str(uuid.uuid4()),
            search_id=search_id,
            position=len(saved_records),
            total_results=len(listings),
        )
        await self.cursor_repository.save(cursor)
        
        # Emit search complete event
        complete_event = self.event_emitter.create_search_complete_event(
            search_id=search_id,
            results_count=len(saved_records),
            correlation_id=correlation_id,
        )
        self.event_emitter.emit(complete_event)
        
        return ActionResult(
            action_id=action.id,
            success=True,
            data={
                "jobs": [record.to_dict() for record in saved_records],
                "search_id": search_id,
                "cursor_id": cursor.id,
                "new_jobs_count": len(saved_records),
                "total_jobs_count": len(listings),
            },
            events=self.event_emitter.get_history(),
        )

    async def _execute_jobs_get(self, action: ActionEnvelope) -> ActionResult:
        """Execute jobs.get action to fetch detailed job information.
        
        Requires either:
        1. A full JobSummary object in the payload (from search results), OR
        2. Both job_id and url in the payload to construct a minimal summary
        
        Enrichment verification is always performed to ensure summary/detail identity match.
        """
        correlation_id = action.correlation_id or action.id
        
        # Check for full JobSummary in payload (preferred path)
        summary_data = action.payload.get("summary")
        if summary_data:
            from packages.domain_jobs.summary_parser import JobSummary
            try:
                summary = JobSummary(**summary_data)
            except Exception as exc:
                return ActionResult(
                    action_id=action.id,
                    success=False,
                    error=f"Invalid summary in payload: {exc}",
                )
        else:
            # Fallback: require job_id and url to construct minimal summary
            job_id = action.payload.get("job_id")
            job_url = action.payload.get("url")
            
            if not job_id or not job_url:
                return ActionResult(
                    action_id=action.id,
                    success=False,
                    error="Missing required fields: either 'summary' object or both 'job_id' and 'url'",
                )
            
            from packages.domain_jobs.summary_parser import JobSummary
            summary = JobSummary(
                job_id=job_id,
                title="",  # Will be verified against detail
                url=job_url,
                description="",  # Will be verified against detail
                posted_date=""  # Will be verified against detail
            )
        
        # Get or create Camofox session
        session_config = self._build_session_config(action.account_id)
        session = await self.session_manager.get_session(action.account_id, session_config)
        
        # Emit session launched event
        session_event = Event(
            type=EventType.SESSION_LAUNCHED,
            data={"account_id": action.account_id},
            correlation_id=correlation_id,
        )
        self.event_emitter.emit(session_event)
        
        # Execute job detail fetch via Camofox session with enrichment verification
        jobs_search = JobsSearch(session)
        
        try:
            # Always verify enrichment to ensure summary/detail identity match
            listing = await jobs_search.get_job_details(summary, verify_enrichment=True)
        except Exception as exc:
            return ActionResult(
                action_id=action.id,
                success=False,
                error=f"Failed to fetch job details: {exc}",
            )
        
        # Normalize to job record
        record = self.normalizer.normalize(listing)
        
        # Save record
        self.job_storage[record.id] = record
        
        # Emit job found event
        job_event = self.event_emitter.create_job_found_event(
            job_record=record.to_dict(),
            correlation_id=correlation_id,
        )
        self.event_emitter.emit(job_event)
        
        return ActionResult(
            action_id=action.id,
            success=True,
            data={
                "job": record.to_dict(),
            },
            events=self.event_emitter.get_history(),
        )

    def _build_session_config(self, account_id: str) -> SessionConfig:
        """Build session configuration for account.
        
        Loads persisted credentials if available for automatic session reuse.
        Falls back to empty config if no credentials exist.
        """
        # Try to load persisted credentials
        credentials = CamofoxSession.load_persisted_credentials()
        
        if credentials:
            # Use persisted credentials for automatic session reuse
            return CamofoxSession.create_config_from_credentials(
                account_id=account_id,
                credentials=credentials
            )
        else:
            # No persisted credentials - return empty config
            # Session will require manual authentication
            return SessionConfig(
                account_id=account_id,
                cookies=[],
                humanization=HumanizationConfig(),
            )
