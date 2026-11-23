# T-008: Website Agent: site content, static renderer and Netlify deploy adapter

| | |
|---|---|
| **Wave** | 1 |
| **Depends on** | T-001 |
| **ADRs** | [ADR-0015](../docs/adr/0015-website-generation-qa-and-deploy-loop.md), [ADR-0009](../docs/adr/0009-agent-message-and-handoff-protocol.md), [ADR-0010](../docs/adr/0010-llm-provider-abstraction-and-fake.md), [ADR-0011](../docs/adr/0011-external-service-ports-rdap-and-hosting.md), [ADR-0008](../docs/adr/0008-shared-domain-contracts.md), [ADR-0023](../docs/adr/0023-reliability-timeouts-retries-and-failure-states.md) |
| **Status** | todo |

## Goal

The product can turn what the founder said into a clean, accessible static website
(HTML/CSS, no build step), revise it from chat change requests, fix it from QA issues,
and publish it to Netlify when a token is configured.

## Owns (only these paths may change)

- `launch_agents/agents/website/`
- `launch_agents/adapters/netlify.py`
- `tests/test_website_agent.py`
- `tests/test_site_renderer.py`
- `tests/test_netlify.py`
- `evidence/T-008/`
- `prs/T-008.md`

## Contracts

- **Provides:** `WebsiteAgent` (Specialist, `AgentId.WEBSITE`); `generate_content`, `revise_content`, `fix_content`, `render_site`, `required_pages` (ADR-0015); `WebsiteIntent`; `NetlifySiteHost` (ADR-0011); `FAKE_HANDLERS` for `website.intent`, `website.generate`, `website.revise`, `website.fix`, `website.reply`.
- **Consumes:** `SiteContent` and related types, `SiteBundle`, `QaIssue`, `BuildWebsite`, `DeployWebsite`, `OpenView`, `WebsitePatch`, `SiteHost`, `DeployResult`, `slugify` (T-001).
- **LLM context keys:** `website.generate` -> `{"company_name", "business_description", "pages", "services", "about", "contact", "founders": [names], "extra_content", "style_notes"}`; `website.revise` adds `{"content": SiteContent json, "change_request"}`; `website.fix` adds `{"content", "issues": [QaIssue json]}`; `website.intent` -> `{"text", "has_build": bool, "last_qa_passed": bool | None}`.

## Acceptance criteria

1. `render_site` follows every renderer rule in ADR-0015 (doctype, lang, charset, viewport, title format, nav linking all pages, one h1, no skipped levels, footer contact, inline SVG logo with `role="img"` + `aria-label`, escaped text, CSS custom properties with AA-safe defaults, focus styles, mobile-first CSS, no JS or external assets) and is byte-for-byte deterministic.
2. Page slugs: "Home" -> `index.html`, other names -> kebab-case; the nav order follows `content.pages`.
3. `WebsiteAgent.handle`: build/change requests return `BuildWebsite(change_request)` + `OpenView("website")` and a short message saying QA will check it; requirements in the message (e.g. "add a Pricing page") come back as `facts_patch.website`; without a company name it asks the founder to pick a name first (no action); "deploy" returns `DeployWebsite(override_qa=False)`; only an explicit "deploy anyway"/"I accept the QA issues" sets `override_qa=True`; questions use `website.reply`. Task done (deploy requested) -> `hand_back=True`.
4. Fake handlers are deterministic: `website.generate` builds content from the context (all required pages, services, founders, contact) but **deliberately leaves out `extra_content` items** on the first draft (documented in `fake.py`) so the demo shows a QA fix round; `website.fix` adds a section for each missing page/content/contact issue; `website.revise` handles "add a X page" and otherwise adds a section to the home page.
5. `NetlifySiteHost` (tests with `httpx.MockTransport`): finds or creates the site, uploads the zip with `Content-Type: application/zip`, polls until ready, returns the `ssl_url`; a name clash retries with a suffix; HTTP errors, timeouts and `error` state return `status="failed"` with a friendly message; the bearer token is never logged or put in messages.
6. Reliability (ADR-0023): every Netlify request has a 30 s timeout and up to 2 retries on 429/5xx via `call_with_retry`; the deploy poll stops after 60 s; a failure that survives the retries returns `status="failed"` with a friendly message (ADR-0011: `deploy` never raises), and the founder can retry from the Website screen.
7. `LLMOutputError` in generate/revise/fix surfaces as `LLMOutputError` to the caller (the pipeline handles it); in `handle` it becomes a friendly message.

## Feature run (`evidence/T-008/feature_run.py`)

With `FakeLLM`: generates content for the sample (company "Crumb Ledger", services,
contact email, extra content "testimonials"), renders it and prints the file list, the
nav and the first 30 lines of `index.html`; applies a change request "add a Pricing page"
and prints the new file list; applies `fix_content` with a missing-content issue and shows
the added section; deploys the bundle through `NetlifySiteHost` against a `MockTransport`
that simulates create -> deploy -> ready and prints the URL. Writes the rendered site to a
temp dir and prints its path.

## Out of scope

QA checks (T-009), the build -> QA -> fix loop and persistence (T-013), preview UI (T-022).
