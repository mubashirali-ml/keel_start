# T-020: Legal documents with electronic signatures, signed downloads, and the Audit trail

| | |
|---|---|
| **Wave** | 4 |
| **Depends on** | T-011, T-016, T-017, T-039 |
| **ADRs** | [ADR-0031](../docs/adr/0031-electronic-signatures-and-signed-pdfs.md), [ADR-0035](../docs/adr/0035-frontend-v2-brand-routes-layout-and-feature-boundaries.md), [ADR-0014](../docs/adr/0014-founding-documents-and-signoff-state-machine.md), [ADR-0032](../docs/adr/0032-services-and-http-api-v2.md), [ADR-0026](../docs/adr/0026-accounts-sessions-request-context-and-authorization.md), [ADR-0030](../docs/adr/0030-plans-billing-stripe-and-entitlements.md), [ADR-0036](../docs/adr/0036-ui-recorded-runs-with-accounts-and-demo-seeding-v2.md), [ADR-0005](../docs/adr/0005-frontend-verification-and-browser-recordings.md) |
| **Status** | todo |

## Goal

Each founder reads every founding document, sees its version, status and who has signed,
signs it electronically as themselves (typed full name plus explicit consent), or edits it
and signs the new version, understands clearly when an edit cancelled other signatures or
when they were looking at an old version, downloads the signed PDF and an editable Word
copy, and can review every action in the audit trail.

## Owns (only these paths may change)

- `frontend/src/features/legal/`
- `frontend/src/features/audit/`
- `evidence/T-020/`
- `prs/T-020.md`

## Contracts

- **Provides:** the Legal page and the Audit page (default exports).
- **Consumes:** `@/design` (incl. `PlanGate`, `TrustNote`, `FormField`), `@/api` (`useDocuments`, `useDocument`, `useSignDocument`, `useEditDocument`, `useAudit`, `useCase`, `useMe`, `useConfig` for the consent text, download URLs), demo-mode `ActingFounderContext` (T-011); endpoints from T-017.

## Acceptance criteria

1. Document list: title, kind, `v{n}`, `StatusBadge`, per-founder signature chips (signed with date / waiting); "Legal step complete" banner when all are executed; the not-legal-advice banner always visible.
2. Document view: rendered Markdown with placeholders (`[ADDRESS]` ...) highlighted and a hint "fill these in your downloaded Word copy; never type tax IDs here"; the document fingerprint (first 12 hex of SHA-256) shown.
3. **Sign dialog**: shows document title and version, a "Type your full name" field (validated against the founder's name with a helpful message), the consent checkbox with `ESIGN_CONSENT_TEXT` from config (unchecked by default), the `TrustNote` ("We record time, account, IP address and a fingerprint of this exact version"), and "Sign as {your name}"; sends version, hash, typed name and consent; success toast "Signed. Bob still needs to sign." The button is disabled with an explanation when the user is not a signer of this document, has already signed, or has not verified their email (with a "Resend email" action).
4. **Edit dialog**: a warning that the other founders' signatures will be cancelled, the editor, then the same typed-name + consent step to sign the new version; saving shows "Version 3 saved and signed by you. Bob's signature was cancelled and he needs to sign again."
5. Stale version (409) shows a clear message, refreshes the document and highlights the new version; no raw codes shown.
6. Downloads: "Download signed PDF" on executed documents and "Download Word copy" on all; on the Free plan both and "Generate documents" are wrapped in `PlanGate`.
7. "Generate documents" when none exist (409 when facts are not locked -> friendly explanation pointing to the chat).
8. Audit: chronological timeline with actor (founder name, agent identity or "System"), plain-words actions ("Bob edited the IP Assignment (v1 → v2) and signed it", "Alice's signature was rejected: the document had changed", "Alice downloaded the signed PDF"), timestamps; filter by document; empty state; in demo mode entries made via "act as" are marked.
9. Component tests cover sign enablement (signer / non-signer / signed / unverified), typed-name validation, consent requirement, edit warning and invalidation message, stale handling, plan gate and audit wording.
10. **Quality bar:** responsive at 390px with no horizontal page scroll, light and dark mode, keyboard accessible with visible focus (dialog focus trap), WCAG AA contrast, loading/empty/error states, no layout shift, friendly copy.
11. **Playwright screenshots** in `evidence/T-020/` at 1280px and 390px, light and dark.

## Feature run (`evidence/T-020/feature_run.py`)

With `running_app(seed_stage="legal", demo_mode=False)`: Alice logs in through the login
page in one browser context and Bob in a second context. Alice opens Legal and asserts
documents, versions and chips; Bob signs one document (typed name + consent) and the chip
updates for Alice after refresh; Alice edits a document and asserts the invalidation
message; Bob, still showing the old version, signs and sees the stale-version message;
both sign everything until "Legal step complete"; Alice downloads a signed PDF and a Word
copy (Playwright `expect_download`, PDF header checked); Audit shows the edit,
invalidation, rejection and download entries. A third run with `plan="free"` asserts the
plan gate. Saves matrices `legal`, `legal-sign` (dialog open), `legal-edit` and `audit`;
checks no horizontal scroll and no raw JSON.

## Out of scope

Cap table view (T-021), chat cards (T-018), the team view (T-044).
