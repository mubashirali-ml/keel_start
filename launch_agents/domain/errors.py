"""Error types (ADR-0008, ADR-0023, ADR-0026).

Every ``message`` is friendly, founder-facing English: the API shows it as-is.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "AlreadySignedError",
    "AuthRequiredError",
    "ConflictError",
    "CsrfError",
    "DeployBlockedError",
    "EmailNotVerifiedError",
    "ExternalServiceError",
    "FactsNotReadyError",
    "ForbiddenError",
    "InvalidCredentialsError",
    "InvalidStateError",
    "LLMOutputError",
    "LaunchError",
    "NameNotChosenError",
    "NotASignerError",
    "NotExecutedError",
    "NotFoundError",
    "PaymentProviderError",
    "PlanRequiredError",
    "RateLimitedError",
    "RetryableError",
    "StaleVersionError",
    "TokenInvalidError",
    "UsageLimitError",
    "WebhookSignatureError",
]


class LaunchError(Exception):
    """Base class of every expected, founder-facing error (ADR-0008)."""

    code: str = "error"
    http_status: int = 400

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details: dict[str, Any] = dict(details or {})

    def __repr__(self) -> str:
        return f"{type(self).__name__}(code={self.code!r}, message={self.message!r})"


# ADR-0008
class NotFoundError(LaunchError):
    code = "not_found"
    http_status = 404


class InvalidStateError(LaunchError):
    code = "invalid_state"
    http_status = 422


class FactsNotReadyError(LaunchError):
    code = "facts_not_ready"
    http_status = 409


class NameNotChosenError(LaunchError):
    code = "name_not_chosen"
    http_status = 409


class StaleVersionError(LaunchError):
    code = "stale_version"
    http_status = 409


class NotASignerError(LaunchError):
    code = "not_a_signer"
    http_status = 403


class AlreadySignedError(LaunchError):
    code = "already_signed"
    http_status = 409


class DeployBlockedError(LaunchError):
    code = "qa_failed_needs_override"
    http_status = 409


class LLMOutputError(LaunchError):
    code = "llm_unavailable"
    http_status = 502


class ExternalServiceError(LaunchError):
    code = "external_service"
    http_status = 502


# ADR-0023
class RetryableError(LaunchError):
    """A transient failure: the caller may try again later (ADR-0023)."""

    code = "temporarily_unavailable"
    http_status = 503


# ADR-0026
class AuthRequiredError(LaunchError):
    code = "auth_required"
    http_status = 401


class InvalidCredentialsError(LaunchError):
    code = "invalid_credentials"
    http_status = 401


class ForbiddenError(LaunchError):
    code = "forbidden"
    http_status = 403


class EmailNotVerifiedError(LaunchError):
    code = "email_not_verified"
    http_status = 403


class CsrfError(LaunchError):
    code = "csrf_failed"
    http_status = 403


class PlanRequiredError(LaunchError):
    code = "plan_required"
    http_status = 402


class RateLimitedError(LaunchError):
    """``details.retry_after_s`` says when to try again (ADR-0033)."""

    code = "rate_limited"
    http_status = 429


class UsageLimitError(LaunchError):
    code = "usage_limit"
    http_status = 429


class ConflictError(LaunchError):
    code = "conflict"
    http_status = 409


class TokenInvalidError(LaunchError):
    code = "token_invalid"
    http_status = 400


class NotExecutedError(LaunchError):
    code = "not_executed"
    http_status = 409


class PaymentProviderError(LaunchError):
    code = "payment_provider"
    http_status = 502


class WebhookSignatureError(LaunchError):
    code = "webhook_invalid"
    http_status = 400
