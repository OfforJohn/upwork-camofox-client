"""Domain camofox package for Camofox session management."""

from .session import (
    CamofoxSession,
    SessionManager,
    SessionConfig,
    ProxyConfig,
    HumanizationConfig,
    Cookie,
    SessionState,
)
from .interface import BrowserInterface, FakeBrowser, PageInfo

__all__ = [
    "CamofoxSession",
    "SessionManager",
    "SessionConfig",
    "ProxyConfig",
    "HumanizationConfig",
    "Cookie",
    "SessionState",
    "BrowserInterface",
    "FakeBrowser",
    "PageInfo",
]
