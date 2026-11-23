"""Signed PDF and editable Word copies of founding documents (ADR-0031, branding ADR-0039). Owned by T-031.

``reportlab`` and ``python-docx`` are imported lazily inside the implementation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Mapping, Sequence

from pydantic import BaseModel

from ..domain.constants import BRAND_NAME
from ..domain.documents import AuditEntry, Document

__all__ = ["Block", "SignerInfo", "markdown_blocks", "render_docx", "render_signed_pdf"]


class SignerInfo(BaseModel):
    """Per founder id: the name and account email printed on the signature page."""

    full_name: str
    email: str | None = None


class Block(BaseModel):
    """One block of the small Markdown subset the Law Agent writes."""

    kind: Literal["heading", "paragraph", "bullet_list", "numbered_list"]
    level: int = 0  # heading level (1..6); 0 otherwise
    text: str = ""  # heading / paragraph text with inline **bold** / *italic* markers
    items: list[str] = []  # list items


def render_signed_pdf(
    doc: Document,
    *,
    company_name: str,
    signers: Mapping[str, SignerInfo],
    audit: Sequence[AuditEntry],
    generated_at: datetime,
    brand_name: str = BRAND_NAME,
) -> bytes:
    """Executed documents only (else ``NotExecutedError``): body, signature page, certificate of
    completion, footers; deterministic bytes (reportlab ``invariant=1``) (T-031)."""
    raise NotImplementedError("render_signed_pdf is implemented in T-031")


def render_docx(doc: Document, *, company_name: str, brand_name: str = BRAND_NAME) -> bytes:
    """Editable Word copy with placeholders highlighted, "not the signed record" (T-031)."""
    raise NotImplementedError("render_docx is implemented in T-031")


def markdown_blocks(content: str) -> list[Block]:
    """Headings, paragraphs, bullet and numbered lists of the document Markdown (T-031)."""
    raise NotImplementedError("markdown_blocks is implemented in T-031")
