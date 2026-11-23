"""Authorization for every company endpoint (ADR-0026). Owned by T-027."""

from .policy import ROLE_PERMISSIONS, authorize_case

__all__ = ["ROLE_PERMISSIONS", "authorize_case"]
