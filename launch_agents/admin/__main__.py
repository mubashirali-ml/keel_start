"""CLI: ``python -m launch_agents.admin grant-admin <email> | revoke-admin <email>`` (ADR-0034). Owned by T-038."""

from __future__ import annotations

from typing import Sequence

__all__ = ["main"]


def main(argv: Sequence[str] | None = None) -> int:
    """Change ``is_admin``, print a confirmation, exit non-zero for an unknown email (T-038)."""
    raise NotImplementedError("the admin CLI is implemented in T-038")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
