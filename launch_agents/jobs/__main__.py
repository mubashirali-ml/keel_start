"""CLI: ``python -m launch_agents.jobs worker [--once]`` (ADR-0028). Owned by T-030."""

from __future__ import annotations

from typing import Sequence

__all__ = ["main"]


def main(argv: Sequence[str] | None = None) -> int:
    """Run the worker loop (``--once``: one job), with clean shutdown on Ctrl+C / SIGTERM (T-030)."""
    raise NotImplementedError("the jobs CLI is implemented in T-030")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
