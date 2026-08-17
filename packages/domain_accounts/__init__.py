"""Domain accounts package for account state and AuthGuard."""

from .auth_guard import AuthGuard, AuthValidationResult

__all__ = ["AuthGuard", "AuthValidationResult"]
