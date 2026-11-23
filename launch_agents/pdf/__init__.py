"""Signed PDF and Word rendering (ADR-0031, ADR-0039). Owned by T-031."""

from .render import Block, SignerInfo, markdown_blocks, render_docx, render_signed_pdf

__all__ = ["Block", "SignerInfo", "markdown_blocks", "render_docx", "render_signed_pdf"]
