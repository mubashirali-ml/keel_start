# T-020: Legal documents with multi-founder sign-off, and the Audit trail

| | |
|---|---|
| **Wave** | 4 |
| **Depends on** | T-011, T-016, T-017 |
| **ADRs** | [ADR-0019](../docs/adr/0019-frontend-design-system-and-app-layout.md), [ADR-0014](../docs/adr/0014-founding-documents-and-signoff-state-machine.md), [ADR-0017](../docs/adr/0017-services-and-http-api-surface.md), [ADR-0020](../docs/adr/0020-ui-recorded-runs-and-demo-seeding.md), [ADR-0005](../docs/adr/0005-frontend-verification-and-browser-recordings.md) |
| **Status** | todo |

## Goal

Founders read each founding document, see its version and status, see who has signed,
approve it or edit it as the selected founder, understand clearly when an edit cancelled
other signatures or when they were looking at an old version, and can review every action
in the audit trail.

## Owns (only these paths may change)

- `frontend/src/features/legal/`
- `frontend/src/features/audit/`
- `evidence/T-020/`
- `prs/T-020.md`

## Contracts

- **Provides:** the Legal page and the Audit page (default exports).
- **Consumes:** `@/design`, `@/api` (`useDocuments`, `useSignDocument`, `useEditDocument`, `useAudit`, `useCase`, document generation), `ActingFounderContext` (T-011); endpoints from T-017.

## Acceptance criteria

1. Document list: title, kind, `v{n}`, `StatusBadge` (awaiting signatures / executed), per-founder signature chips (signed / waiting) for required signers; a "Legal step complete" banner when all are executed; the legal-notice banner is always visible.
2. Document view: rendered markdown with placeholders (`[ADDRESS]` …) visually highlighted; "Approve as {acting founder}" (disabled with an explanation if they are not a required signer or already signed); "Edit" opens an editor dialog with a warning that other founders' approvals will be cancelled; saving shows "Version 3 saved. Bob's approval was cancelled and he needs to approve again."
3. Stale version: a 409 `stale_version` shows a clear message, refreshes the document and highlights the new version; no raw error codes are shown.
4. "Generate documents" when none exist (409 when facts are not locked -> friendly explanation pointing to the chat).
5. Audit: chronological timeline with actor (founder name, agent identity or "System"), action in plain words ("Bob edited the IP Assignment (v1 → v2)", "Alice's approval was rejected: the document had changed"), timestamp; filter by document; empty state.
6. A visible note says approvals are recorded in the app and are not legal e-signatures in this release.
7. Component tests cover signing enablement per founder, edit warning and invalidation message, stale handling and audit wording.
8. **Quality bar:** responsive at 390px with no horizontal page scroll, light and dark mode, keyboard accessible with visible focus (dialog focus trap), WCAG AA contrast, loading/empty/error states, no layout shift, friendly copy.
9. **Playwright screenshots** in `evidence/T-020/` at 1280px and 390px, light and dark.

## Feature run (`evidence/T-020/feature_run.py`)

With `running_app(seed_stage="legal")`: opens Legal and asserts the documents, versions
and signature chips; as Bob (founder switcher) approves one document; as Alice edits a
document and asserts the invalidation message; opens a second browser page still showing
the old version and approves there, asserting the stale-version message; signs everything
as the right founders until the "Legal step complete" banner appears; opens Audit and
asserts the edit, invalidation and rejected entries. Saves matrices `legal`, `legal-edit`
(dialog open) and `audit`; checks no horizontal scroll and no raw JSON.

## Out of scope

Cap table view (T-021), chat cards (T-018).
