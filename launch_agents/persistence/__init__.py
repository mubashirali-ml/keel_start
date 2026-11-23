"""Persistence (ADR-0027): one schema (``tables.py``, T-001), the engine and case
``Repository`` (T-005) and one repository per area (owners named in each module).

Pydantic domain objects are the only thing crossing a repository boundary; ORM rows never
leave this package. Every method runs in its own transaction; ``Repository.transaction()``
groups writes. Each repository takes an ``Engine`` and works on SQLite and PostgreSQL.
"""

from .tables import TABLE_NAMES, metadata

__all__ = ["TABLE_NAMES", "metadata"]
