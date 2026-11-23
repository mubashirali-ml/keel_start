# Backlog

Plan for building [the product brief](../docs/product-brief.md). Architecture decisions: [docs/adr/](../docs/adr/README.md).
Machine-readable twin: [plan.json](plan.json). Product decisions log: [product-decisions.md](../docs/product-decisions.md).

Tickets in the same wave own disjoint paths and run in parallel; each depends only on earlier waves.

## Wave 0

Foundation: shared vocabulary, stand-ins for the AI and outside services, and placeholders, so ten pieces can be built at the same time next. Nothing to look at yet.

| Ticket | Title | Depends on | Owns | Status |
|---|---|---|---|---|
| [T-001](T-001-foundation-skeleton-contracts-and-fakes.md) | Foundation: package skeleton, shared contracts, LLM abstraction, fakes and typed stubs | — | `launch_agents/`<br>`tests/conftest.py`<br>`tests/test_foundation.py`<br>`pytest.ini`<br>`.env.example`<br>`evidence/T-001/`<br>`prs/T-001.md` | todo |

## Wave 1

Ten pieces built in parallel: the automatic rules (equity, vesting, 83(b), cap table, approvals), saving, the five specialist agents, and the app's look and feel. You can open the app's component gallery and empty layout in light and dark mode.

| Ticket | Title | Depends on | Owns | Status |
|---|---|---|---|---|
| [T-002](T-002-case-validation-rules.md) | Case validation rules (equity, vesting, 83(b), missing facts) | T-001 | `launch_agents/rules/validation.py`<br>`tests/test_validation.py`<br>`evidence/T-002/`<br>`prs/T-002.md` | todo |
| [T-003](T-003-cap-table-vesting-and-exports.md) | Cap Table Builder: share allocation, vesting schedule, CSV and Excel export | T-001 | `launch_agents/rules/cap_table.py`<br>`launch_agents/rules/exports.py`<br>`tests/test_cap_table.py`<br>`tests/test_cap_table_exports.py`<br>`evidence/T-003/`<br>`prs/T-003.md` | todo |
| [T-004](T-004-signoff-state-machine.md) | Multi-party sign-off state machine with audit entries | T-001 | `launch_agents/signoff/`<br>`tests/test_signoff.py`<br>`evidence/T-004/`<br>`prs/T-004.md` | todo |
| [T-005](T-005-persistence-sqlite-repository.md) | Persistence: SQLite schema and Repository | T-001 | `launch_agents/persistence/`<br>`tests/test_persistence.py`<br>`evidence/T-005/`<br>`prs/T-005.md` | todo |
| [T-006](T-006-law-agent-and-document-drafting.md) | Law Agent: legal Q&A, issue spotting and founding-document drafting | T-001 | `launch_agents/agents/law/`<br>`tests/test_law_agent.py`<br>`tests/test_law_documents.py`<br>`evidence/T-006/`<br>`prs/T-006.md` | todo |
| [T-007](T-007-name-agent-and-rdap-checks.md) | Name Agent with live RDAP domain checks | T-001 | `launch_agents/agents/name/`<br>`launch_agents/adapters/rdap.py`<br>`tests/test_name_agent.py`<br>`tests/test_rdap.py`<br>`evidence/T-007/`<br>`prs/T-007.md` | todo |
| [T-008](T-008-website-agent-renderer-and-netlify.md) | Website Agent: site content, static renderer and Netlify deploy adapter | T-001 | `launch_agents/agents/website/`<br>`launch_agents/adapters/netlify.py`<br>`tests/test_website_agent.py`<br>`tests/test_site_renderer.py`<br>`tests/test_netlify.py`<br>`evidence/T-008/`<br>`prs/T-008.md` | todo |
| [T-009](T-009-qa-agent-site-checks.md) | QA Agent: requirement and quality checks for generated websites | T-001 | `launch_agents/agents/qa/`<br>`tests/test_qa_agent.py`<br>`evidence/T-009/`<br>`prs/T-009.md` | todo |
| [T-010](T-010-registration-guide-agent.md) | Registration Guide Agent with curated Delaware and Wyoming data | T-001 | `launch_agents/agents/guide/`<br>`tests/test_guide_agent.py`<br>`evidence/T-010/`<br>`prs/T-010.md` | todo |
| [T-011](T-011-frontend-design-system-and-app-shell.md) | Frontend foundation: design system, themes, app shell with agent-aware chat layout, typed API client, UI-run helper | T-001 | `frontend/`<br>`launch_agents/devtools/`<br>`tests/test_devtools.py`<br>`evidence/T-011/`<br>`prs/T-011.md` | todo |

## Wave 2

The Manager joins everything up: one conversation that gathers facts and hands over to specialists, plus the legal, website and case services behind it.

| Ticket | Title | Depends on | Owns | Status |
|---|---|---|---|---|
| [T-012](T-012-manager-agent-and-turn-graph.md) | Manager Agent and the LangGraph turn graph (routing, handoffs, fact gathering) | T-001, T-002, T-006, T-007, T-008, T-010 | `launch_agents/agents/manager/`<br>`launch_agents/orchestrator/`<br>`tests/test_manager_agent.py`<br>`tests/test_orchestrator.py`<br>`evidence/T-012/`<br>`prs/T-012.md` | todo |
| [T-013](T-013-website-pipeline-and-service.md) | Website pipeline and service: build, QA, automatic fixes, deploy gate | T-001, T-005, T-008, T-009 | `launch_agents/pipelines/`<br>`launch_agents/workflows/website.py`<br>`tests/test_website_pipeline.py`<br>`tests/test_website_service.py`<br>`evidence/T-013/`<br>`prs/T-013.md` | todo |
| [T-014](T-014-case-service-conversation-and-progress.md) | Case service: conversations, action execution, names, checklist and progress | T-001, T-002, T-005, T-007, T-010 | `launch_agents/workflows/case.py`<br>`tests/test_case_service.py`<br>`evidence/T-014/`<br>`prs/T-014.md` | todo |
| [T-015](T-015-legal-service-cap-table-documents-signoff.md) | Legal service: cap table, document generation, sign-off and audit trail | T-001, T-002, T-003, T-004, T-005, T-006 | `launch_agents/workflows/legal.py`<br>`tests/test_legal_service.py`<br>`evidence/T-015/`<br>`prs/T-015.md` | todo |

## Wave 3

The complete backend API (FastAPI) and ready-made demo companies at every stage of the journey.

| Ticket | Title | Depends on | Owns | Status |
|---|---|---|---|---|
| [T-016](T-016-api-core-composition-and-demo-seed.md) | HTTP API core, composition root and demo seeding | T-012, T-013, T-014, T-015 | `launch_agents/api/__init__.py`<br>`launch_agents/api/app.py`<br>`launch_agents/api/errors.py`<br>`launch_agents/api/deps.py`<br>`launch_agents/api/schemas.py`<br>`launch_agents/api/routes/__init__.py`<br>`launch_agents/api/routes/cases.py`<br>`launch_agents/composition.py`<br>`launch_agents/demo/`<br>`tests/test_api_cases.py`<br>`tests/test_composition.py`<br>`tests/test_demo_seed.py`<br>`evidence/T-016/`<br>`prs/T-016.md` | todo |
| [T-017](T-017-api-legal-cap-table-and-website-routes.md) | HTTP API: cap table, documents and sign-off, audit, and website routes | T-005, T-013, T-015 | `launch_agents/api/routes/legal.py`<br>`launch_agents/api/routes/website.py`<br>`tests/test_api_legal.py`<br>`tests/test_api_website.py`<br>`evidence/T-017/`<br>`prs/T-017.md` | todo |

## Wave 4

All screens: chat and overview, names and domains, legal and audit, cap table, website, registration guide; each checked in a real browser with screenshots.

| Ticket | Title | Depends on | Owns | Status |
|---|---|---|---|---|
| [T-018](T-018-chat-and-overview-screens.md) | Chat experience and Overview screen | T-011, T-016, T-017 | `frontend/src/features/chat/`<br>`frontend/src/features/overview/`<br>`evidence/T-018/`<br>`prs/T-018.md` | todo |
| [T-019](T-019-names-domains-and-registration-guide-screens.md) | Names & Domains screen and Registration Guide checklist | T-011, T-016, T-017 | `frontend/src/features/names/`<br>`frontend/src/features/guide/`<br>`evidence/T-019/`<br>`prs/T-019.md` | todo |
| [T-020](T-020-legal-signoff-and-audit-screens.md) | Legal documents with multi-founder sign-off, and the Audit trail | T-011, T-016, T-017 | `frontend/src/features/legal/`<br>`frontend/src/features/audit/`<br>`evidence/T-020/`<br>`prs/T-020.md` | todo |
| [T-021](T-021-cap-table-screen.md) | Cap Table screen: table, ownership chart, vesting timeline, downloads | T-011, T-016, T-017 | `frontend/src/features/cap-table/`<br>`evidence/T-021/`<br>`prs/T-021.md` | todo |
| [T-022](T-022-website-preview-qa-and-deploy-screen.md) | Website screen: live preview, QA report, deploy status and download | T-011, T-016, T-017 | `frontend/src/features/website/`<br>`evidence/T-022/`<br>`prs/T-022.md` | todo |

## Wave 5

The full founder journey from first message to finished company kit, recorded end to end, plus a short run guide.

| Ticket | Title | Depends on | Owns | Status |
|---|---|---|---|---|
| [T-023](T-023-end-to-end-founder-journey.md) | End-to-end founder journey: API test suite and recorded browser demo | T-018, T-019, T-020, T-021, T-022 | `tests/test_e2e_journey.py`<br>`docs/running-the-app.md`<br>`evidence/T-023/`<br>`prs/T-023.md` | todo |

## Open questions for the product owner

Each has a default already applied in the plan; confirm or change it.

| Id | Ticket | Question | Recommended |
|---|---|---|---|
| Q-001 | T-006 | Who needs to approve each founder's 83(b) tax election form? | Only that founder |
| Q-002 | T-008 | Which hosting service should publish the founder's website? | Netlify |
| Q-003 | T-004 | Can a founder still edit a document after every founder has approved it? | Yes, everyone re-approves |
| Q-004 | T-003 | When does founder vesting start? | On the incorporation date |
| Q-005 | T-008 | Which pages should the website have when the founder doesn't say? | Home, About, Services, Contact |
