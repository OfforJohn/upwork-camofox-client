"""Browser interface for injectable Camofox integration."""

from abc import ABC, abstractmethod
from typing import Optional, List
from dataclasses import dataclass


@dataclass
class PageInfo:
    """Information about the current page."""
    title: str
    url: str


class BrowserInterface(ABC):
    """Abstract interface for browser operations."""

    @abstractmethod
    async def navigate(self, url: str) -> None:
        """Navigate to a URL."""
        pass

    @abstractmethod
    async def get_page_info(self) -> PageInfo:
        """Get current page title and URL."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the browser session."""
        pass

    @abstractmethod
    async def is_active(self) -> bool:
        """Check if the browser session is active."""
        pass


class FakeBrowser(BrowserInterface):
    """Fake browser implementation for testing."""

    def __init__(self, should_authenticate: bool = True, should_fail_navigate: bool = False):
        self._should_authenticate = should_authenticate
        self._should_fail_navigate = should_fail_navigate
        self._current_url = ""
        self._current_title = ""
        self._is_active = False

    async def navigate(self, url: str) -> None:
        """Navigate to a URL."""
        if self._should_fail_navigate:
            raise RuntimeError("Navigation failed")
        self._current_url = url
        self._current_title = "Upwork" if "upwork.com" in url else "Unknown"
        self._is_active = True

    async def get_page_info(self) -> PageInfo:
        """Get current page title and URL."""
        return PageInfo(title=self._current_title, url=self._current_url)

    async def close(self) -> None:
        """Close the browser session."""
        self._is_active = False

    async def is_active(self) -> bool:
        """Check if the browser session is active."""
        return self._is_active
