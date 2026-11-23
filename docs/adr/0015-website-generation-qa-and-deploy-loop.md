# ADR-0015: Website generation, QA checks and the fix-and-deploy loop

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-23 |
| **Deciders** | Supervisor |
| **Tickets** | T-001 (types), T-008 (Website Agent + renderer), T-009 (QA Agent), T-013 (pipeline + service), T-022 (UI) |
| **Scope** | `launch_agents/domain/website.py`, `agents/website/`, `agents/qa/`, `pipelines/website.py`, `workflows/website.py` |

## Context

The Website Agent builds a static HTML/CSS site (no build step) from what the founder
said, shows a preview, takes change requests in the chat, and deploys live. The QA Agent
checks every build against the founder's requirements before every deploy; on fail the
Website Agent fixes it (at most 2 automatic fix rounds); a site that still fails is not
deployed without the founder's explicit OK. QA must be reliable enough to test.

## Decision

**The LLM writes content, code renders HTML.** The LLM returns structured `SiteContent`;
a deterministic renderer turns it into HTML/CSS. QA is mostly deterministic checks on the
rendered files plus one LLM review of requirement coverage.

### Types (`domain/website.py`)

```python
class SiteSection(BaseModel): heading: str; body: str; items: list[str] = []
class SitePage(BaseModel):
    slug: str                    # "index" for the home page, else kebab-case ("about", "services")
    title: str; nav_label: str; sections: list[SiteSection]
class SiteContact(BaseModel): email: str | None = None; phone: str | None = None; address: str | None = None
class SiteFounder(BaseModel): name: str; bio: str
class SiteContent(BaseModel):
    company_name: str; tagline: str; pages: list[SitePage]
    contact: SiteContact; founders: list[SiteFounder]; footer_note: str = ""
class SiteFile(BaseModel): path: str; content: str; content_type: str     # "index.html", "about.html", "styles.css"
class SiteBundle(BaseModel):
    files: list[SiteFile]
    def get(self, path: str) -> SiteFile | None: ...
    def to_zip(self) -> bytes: ...                    # implemented in T-001, deterministic (fixed timestamps)
class QaCheckId(str, Enum):
    PAGES_PRESENT = "pages_present"; CONTENT_PRESENT = "content_present"
    COMPANY_NAME = "company_name"; CONTACT_DETAILS = "contact_details"
    INTERNAL_LINKS = "internal_links"; IMAGE_ALT = "image_alt"; HEADINGS = "headings"
    HTML_STRUCTURE = "html_structure"; CONTRAST = "contrast"; REQUIREMENTS_REVIEW = "requirements_review"
class QaIssue(BaseModel):
    check: QaCheckId; severity: Literal["error", "warning"]; page: str | None = None; message: str
class QaCheckResult(BaseModel): check: QaCheckId; label: str; passed: bool; issues: list[QaIssue]
class QaReport(BaseModel):
    passed: bool                 # True iff no issue with severity "error"
    round: int                   # 0 = first check, 1..MAX_QA_FIX_ROUNDS after fixes
    checks: list[QaCheckResult]  # always all ten, in QaCheckId order
    checked_at: datetime
class SiteBuildStatus(str, Enum):
    QA_PASSED = "qa_passed"; QA_FAILED = "qa_failed"; DEPLOYED = "deployed"
    DEPLOY_FAILED = "deploy_failed"; DEPLOY_NOT_CONFIGURED = "deploy_not_configured"
class SiteBuild(BaseModel):
    id: str; case_id: str; version: int; content: SiteContent; bundle: SiteBundle
    qa_reports: list[QaReport]; qa_passed: bool; fix_rounds: int; status: SiteBuildStatus
    deploy_url: str | None = None; deploy_message: str | None = None; override_by: str | None = None
    created_at: datetime; updated_at: datetime
class DeployResult(BaseModel):
    status: Literal["deployed", "failed", "not_configured"]; url: str | None = None
    deploy_id: str | None = None; provider: str; message: str
```

### Website Agent (`agents/website/`, T-008)

```python
def generate_content(facts: CaseFacts, llm: LLMProvider) -> SiteContent                 # task website.generate
def revise_content(content: SiteContent, change_request: str, facts: CaseFacts, llm: LLMProvider) -> SiteContent  # website.revise
def fix_content(content: SiteContent, issues: list[QaIssue], facts: CaseFacts, llm: LLMProvider) -> SiteContent  # website.fix
def render_site(content: SiteContent) -> SiteBundle
def required_pages(facts: CaseFacts) -> list[str]     # facts.website.pages or DEFAULT_SITE_PAGES
class WebsiteAgent:  # Specialist; returns BuildWebsite / DeployWebsite actions (ADR-0009)
```

Renderer rules: one `<slug>.html` per page (home = `index.html`) plus `styles.css`;
`<!doctype html>`, `<html lang="en">`, `<meta charset>`, viewport meta, `<title>` =
"{page title} | {company}"; a header with the company name and a `<nav>` linking every
page by relative href; exactly one `<h1>` per page, no skipped heading levels; a footer
with contact details and `footer_note`; the logo is inline SVG with `role="img"` and
`aria-label`; all text HTML-escaped. `styles.css` declares `--color-text`, `--color-bg`,
`--color-accent`, `--color-accent-text` on `:root` with WCAG AA-safe defaults, is
responsive (mobile-first, one breakpoint) and has visible focus styles. No JavaScript,
no external assets, no build step. `render_site` is pure and byte-for-byte deterministic.

### QA Agent (`agents/qa/`, T-009)

```python
def deterministic_checks(bundle: SiteBundle, facts: CaseFacts) -> list[QaCheckResult]      # nine checks
def run_qa(bundle: SiteBundle, facts: CaseFacts, llm: LLMProvider, *, round: int = 0, now: datetime) -> QaReport
def qa_summary_message(report: QaReport) -> ChatMessage     # agent=QA, kind=QA_REPORT
```

| Check | Fails (error) when |
|---|---|
| pages_present | a page in `required_pages(facts)` has no matching file (match by slug of the page name; "Home" -> index) |
| content_present | a service or `extra_content` item does not appear (case-insensitive) in any page text |
| company_name | `facts.company_name` missing from any page `<title>` or header |
| contact_details | a stated contact email/phone/address is missing from the site, or a `mailto:` differs |
| internal_links | an `href` to a local file that is not in the bundle (external links are not fetched) |
| image_alt | an `<img>` without non-empty `alt`, or an `<svg role="img">` without `aria-label` |
| headings | not exactly one `<h1>` per page, or a skipped level |
| html_structure | missing doctype / `lang` / `<title>` / charset / viewport, or unbalanced tags (stdlib `html.parser`) |
| contrast | `--color-text` on `--color-bg` or `--color-accent-text` on `--color-accent` below 4.5:1 |
| requirements_review | LLM `qa.review` reports an unmet requirement (severity from the LLM; LLM failure -> one `warning`, never an error) |

### Pipeline (`pipelines/website.py`, T-013)

```python
class PipelineResult(BaseModel):
    content: SiteContent; bundle: SiteBundle; reports: list[QaReport]; passed: bool; fix_rounds: int
def build_site(facts: CaseFacts, llm: LLMProvider, *, previous: SiteContent | None = None,
               change_request: str | None = None, now: datetime) -> PipelineResult
def deploy_build(build: SiteBuild, host: SiteHost, site_slug: str, *, override_qa: bool) -> DeployResult
```

`build_site`: generate (or revise `previous` with `change_request`) -> render -> `run_qa`
round 0; while failed and `fix_rounds < MAX_QA_FIX_ROUNDS`: `fix_content` with the error
issues -> render -> `run_qa` round n. `deploy_build` raises `DeployBlockedError` when
`not build.qa_passed and not override_qa`. Every change request creates a new build that
goes through QA again, so QA always runs on exactly the bundle that would be deployed.
`site_slug` = `slugify(company_name)` + "-" + first 6 chars of the case id.

`WebsiteService` (`workflows/website.py`, T-013) persists each build, posts chat messages
(Website Agent `site_preview`; QA Agent `qa_report` per round; Website Agent
`deploy_status`), audits `SITE_BUILT`, `SITE_DEPLOYED` and `DEPLOY_OVERRIDE`
(founder id), and maps `DeployResult.status` to `SiteBuildStatus`. Without a hosting
token the status is `deploy_not_configured`, the preview and zip download still work, and
the Website Agent says deploy is not configured.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| A. LLM writes structured content, deterministic renderer (chosen) | Valid HTML by construction; QA deterministic; fixes are targeted | Less design freedom than free-form HTML |
| B. LLM writes raw HTML/CSS | Maximum freedom | Broken markup; flaky QA; hard to fake |
| C. Static site generator + templates via npm | Rich themes | Violates "no build step" |

## Consequences

- QA failures in practice are content gaps (missing page, missing service, wrong contact),
  which is exactly what the fix round can repair.
- Tests can force a failing first draft by scripting the fake `website.generate` response.
