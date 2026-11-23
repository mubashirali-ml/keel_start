"""Website content, bundles, QA reports and builds (ADR-0015)."""

from __future__ import annotations

import io
import zipfile
from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel

__all__ = [
    "DeployResult",
    "QaCheckId",
    "QaCheckResult",
    "QaIssue",
    "QaReport",
    "SiteBuild",
    "SiteBuildStatus",
    "SiteBundle",
    "SiteContact",
    "SiteContent",
    "SiteFile",
    "SiteFounder",
    "SitePage",
    "SiteSection",
]

_ZIP_DATE_TIME = (1980, 1, 1, 0, 0, 0)  # fixed timestamp: zips are byte-for-byte deterministic


class SiteSection(BaseModel):
    heading: str
    body: str
    items: list[str] = []


class SitePage(BaseModel):
    slug: str  # "index" for the home page, else kebab-case ("about", "services")
    title: str
    nav_label: str
    sections: list[SiteSection]


class SiteContact(BaseModel):
    email: str | None = None
    phone: str | None = None
    address: str | None = None


class SiteFounder(BaseModel):
    name: str
    bio: str


class SiteContent(BaseModel):
    company_name: str
    tagline: str
    pages: list[SitePage]
    contact: SiteContact
    founders: list[SiteFounder]
    footer_note: str = ""


class SiteFile(BaseModel):
    path: str  # "index.html", "about.html", "styles.css"
    content: str
    content_type: str


class SiteBundle(BaseModel):
    files: list[SiteFile]

    def get(self, path: str) -> SiteFile | None:
        """The file at ``path`` (leading ``/`` ignored), or None."""
        wanted = path.lstrip("/")
        for f in self.files:
            if f.path == wanted:
                return f
        return None

    def to_zip(self) -> bytes:
        """A zip of every file, in bundle order, byte-identical for identical bundles."""
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for f in self.files:
                info = zipfile.ZipInfo(f.path, date_time=_ZIP_DATE_TIME)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 0
                info.external_attr = 0o644 << 16
                zf.writestr(info, f.content.encode("utf-8"))
        return buffer.getvalue()


class QaCheckId(str, Enum):
    PAGES_PRESENT = "pages_present"
    CONTENT_PRESENT = "content_present"
    COMPANY_NAME = "company_name"
    CONTACT_DETAILS = "contact_details"
    INTERNAL_LINKS = "internal_links"
    IMAGE_ALT = "image_alt"
    HEADINGS = "headings"
    HTML_STRUCTURE = "html_structure"
    CONTRAST = "contrast"
    REQUIREMENTS_REVIEW = "requirements_review"


class QaIssue(BaseModel):
    check: QaCheckId
    severity: Literal["error", "warning"]
    page: str | None = None
    message: str


class QaCheckResult(BaseModel):
    check: QaCheckId
    label: str
    passed: bool
    issues: list[QaIssue]


class QaReport(BaseModel):
    passed: bool  # True iff no issue with severity "error"
    round: int  # 0 = first check, 1..MAX_QA_FIX_ROUNDS after fixes
    checks: list[QaCheckResult]  # always all ten, in QaCheckId order
    checked_at: datetime


class SiteBuildStatus(str, Enum):
    QA_PASSED = "qa_passed"
    QA_FAILED = "qa_failed"
    DEPLOYED = "deployed"
    DEPLOY_FAILED = "deploy_failed"
    DEPLOY_NOT_CONFIGURED = "deploy_not_configured"


class SiteBuild(BaseModel):
    id: str
    case_id: str
    version: int
    content: SiteContent
    bundle: SiteBundle
    qa_reports: list[QaReport]
    qa_passed: bool
    fix_rounds: int
    status: SiteBuildStatus
    deploy_url: str | None = None
    deploy_message: str | None = None
    override_by: str | None = None
    created_at: datetime
    updated_at: datetime


class DeployResult(BaseModel):
    status: Literal["deployed", "failed", "not_configured"]
    url: str | None = None
    deploy_id: str | None = None
    provider: str
    message: str
