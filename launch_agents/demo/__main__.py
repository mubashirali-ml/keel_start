"""CLI: ``python -m launch_agents.demo --stage legal --plan launch --db sqlite:///path.db``
(prints the case id and user emails) (ADR-0036). Owned by T-016."""

from __future__ import annotations

from typing import Sequence

__all__ = ["main"]


def main(argv: Sequence[str] | None = None) -> int:
    raise NotImplementedError("the demo seeding CLI is implemented in T-016")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
