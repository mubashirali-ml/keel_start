# T-019: Names & Domains screen and Registration Guide checklist

| | |
|---|---|
| **Wave** | 4 |
| **Depends on** | T-011, T-016, T-039, T-041 |
| **ADRs** | [ADR-0035](../docs/adr/0035-frontend-v2-brand-routes-layout-and-feature-boundaries.md), [ADR-0011](../docs/adr/0011-external-service-ports-rdap-and-hosting.md), [ADR-0016](../docs/adr/0016-registration-guide-data-and-checklist.md), [ADR-0032](../docs/adr/0032-services-and-http-api-v2.md), [ADR-0036](../docs/adr/0036-ui-recorded-runs-with-accounts-and-demo-seeding-v2.md), [ADR-0005](../docs/adr/0005-frontend-verification-and-browser-recordings.md) |
| **Status** | todo |

## Goal

The founder sees name ideas as cards with live availability badges for `.com`, `.co` and
`.io`, the manual state and trademark checks, and can choose a name; and follows a
state-specific registration checklist they can tick off, with progress saved.

## Owns (only these paths may change)

- `frontend/src/features/names/`
- `frontend/src/features/guide/`
- `evidence/T-019/`
- `prs/T-019.md`

## Contracts

- **Provides:** the Names & Domains page and the Registration Guide page (default exports).
- **Consumes:** `@/design`, `@/api` (`useNames`, `useChooseName`, `useGuide`, `useSetGuideItem`, `useCase`), `useMe` (T-011); endpoints from T-041.

## Acceptance criteria

1. Name cards: name, rationale, one badge per domain (`available` success, `taken` danger, `unknown` neutral with "couldn't check" tooltip), "State name: check manually" with the official search link and the USPTO link (new tab, accessible names); the chosen name is highlighted; "Choose this name" (with a domain picker among available domains) calls the API and shows a toast; "Re-check availability" refreshes with a loading state.
2. Copy is honest: "available at the registry" (not a promise), and never shows "available" for `unknown`.
3. Empty state when no names yet, with a button that sends "Suggest some names" to the chat (via the post-message hook).
4. Guide: header with state, entity, "full guide" or "generic checklist" badge and "Last reviewed {date}"; steps grouped by category with title, detail (markdown), fee, due date (83(b) highlighted with countdown), official links; a `Checkbox` per step saving immediately (optimistic with rollback and an error toast on failure); progress bar `done/total`; the disclaimer.
5. When the guide is not available yet (facts missing -> 409), a friendly empty state explains what the Manager still needs.
6. Component tests cover badge mapping, choose flow, optimistic tick + rollback, and empty states.
7. **Quality bar:** responsive at 390px with no horizontal page scroll, light and dark mode, keyboard accessible with visible focus (checkboxes and cards), WCAG AA contrast, loading/empty/error states, no layout shift, friendly copy.
8. **Playwright screenshots** in `evidence/T-019/` at 1280px and 390px, light and dark.

## Feature run (`evidence/T-019/feature_run.py`)

With `running_app(seed_stage="facts")`, logged in as Alice through the login page: opens Names (empty state), triggers suggestions
through the chat, asserts five cards with three badges each, asks in the chat "is Acme
free?" and asserts the Acme card shows `.com` as Taken (fake checker), chooses a name
and asserts the highlight and the header company name. With `seed_stage="website"`:
opens the Guide, asserts "Last reviewed", the Wyoming steps, the 83(b) due date and the
domain step naming the chosen domain and deployed URL; ticks two steps, reloads and
asserts they stay ticked and progress updated. Saves matrices `names` and `guide`; checks
no horizontal scroll and no raw JSON.

## Out of scope

Chat rendering of name options (T-018), other views.
