# ADR-0019: Frontend design system, app layout and feature boundaries

| | |
|---|---|
| **Status** | Superseded by ADR-0035 |
| **Date** | 2026-11-23 |
| **Deciders** | Supervisor |
| **Tickets** | T-011 (implements), T-018..T-022 (feature screens), T-023 (end to end) |
| **Scope** | `frontend/src/` |

## Context

The brief's quality bar: one set of design tokens and shared components, chat as the
centerpiece with per-agent identity, workspace views beside the chat, a founder switcher,
responsive to phone width, light and dark mode, keyboard accessible, WCAG AA, loading /
empty / error states everywhere, no layout shift, friendly copy. Five feature tickets
build screens in parallel (wave 4), so the shell, tokens, components, API client and the
folder boundaries come first (T-011, wave 1).

## Decision

### Folder layout and owners

```
frontend/src/
  main.tsx, App.tsx                 T-011  providers (QueryClient, Theme, Toast, Router)
  app/                              T-011  AppShell, routes, header, FounderSwitcher, ThemeToggle,
                                           ActingFounderContext, StartScreen (case list / new case)
  design/                           T-011  tokens.css, components/, gallery (route /design)
  agents/                           T-011  agentIdentity.ts (AgentId -> name, icon, accent class), AgentAvatar
  api/                              T-011  types.ts, client.ts, hooks.ts, errors.ts
  lib/                              T-011  format.ts (dates, percents, shares), cn.ts
  test/                             T-011  setup.ts, renderWithProviders.tsx, fixtures.ts
  features/chat/                    T-018  ChatPanel (default export used by the shell)
  features/overview/                T-018
  features/names/                   T-019
  features/guide/                   T-019
  features/legal/                   T-020
  features/audit/                   T-020
  features/cap-table/               T-021
  features/website/                 T-022
```

Each `features/<view>/index.tsx` default-exports a page component
`(props: { caseId: string }) => JSX.Element`; T-011 ships placeholders using `EmptyState`,
and the feature ticket replaces the folder. Feature tests live beside the code
(`*.test.tsx`). Features import only from `@/design`, `@/api`, `@/agents`, `@/lib`,
`@/app` (hooks/context) and their own folder — never from another feature.

### Layout

- **Routes:** `/` StartScreen; `/cases/:caseId/:view?` with `view` in
  `overview | names | legal | cap-table | website | guide | audit` (default `overview`);
  `/design` component gallery (all components, all states, both themes).
- **Desktop (>= 1024px):** header (product mark, company name or "New company", founder
  switcher, theme toggle); body split: chat panel left (min 380px, ~40%), workspace right
  with tabs for the seven views and a 6-step progress strip.
- **Tablet/phone (< 1024px):** header collapses to icons; a segmented control switches
  between **Chat** and **Workspace**; workspace tabs become a horizontally scrollable tab
  list; nothing scrolls horizontally at 390px except that tab list.
- When the API returns `open_view`, the workspace switches to that tab (on phones a
  "View in workspace" button appears in the chat instead of switching away).

### Tokens (`design/tokens.css`, CSS variables; Tailwind maps them in `tailwind.config.ts`)

- Colors (each defined for `:root` light and `.dark`): `bg`, `surface`, `surface-raised`,
  `border`, `border-strong`, `text`, `text-muted`, `text-subtle`, `primary`, `primary-fg`,
  `success`, `success-fg`, `warning`, `warning-fg`, `danger`, `danger-fg`, `info`, `info-fg`,
  `focus-ring`, and agent accents `agent-manager` (indigo), `agent-law` (violet),
  `agent-name` (emerald), `agent-website` (sky), `agent-qa` (amber), `agent-guide` (rose),
  `agent-cap-table` (teal), `agent-signoff` (slate). Every text/background pair used must
  reach 4.5:1 (3:1 for large text and icons); T-011's tests compute the ratios from the
  token file.
- Type scale: `xs 12/16`, `sm 14/20`, `base 16/24`, `lg 18/28`, `xl 20/28`, `2xl 24/32`,
  `3xl 30/36`; font Inter Variable, system fallback.
- Spacing: Tailwind's 4px scale. Radius: `sm 6px`, `md 10px`, `lg 14px`, `xl 20px`,
  `full`. Shadow: `sm`, `md`, `lg` (softer in dark mode). Motion: 150ms/250ms,
  disabled under `prefers-reduced-motion`.
- Theme: `system` default, toggle light/dark/system, persisted in `localStorage`
  key `launch.theme`, applied as the `dark` class on `<html>` before first paint
  (inline script in `index.html`, no flash).

### Shared components (`design/components/`, exported from `@/design`)

`Button` (primary/secondary/ghost/danger, sizes, loading), `IconButton` (required
`aria-label`), `Input`, `Textarea`, `Select`, `Checkbox`, `Card`, `Tabs`, `Badge`
(neutral/success/warning/danger/info, always icon + text), `StatusBadge` (maps
`StepStatus`, `DocumentStatus`, `DomainStatus`, `SiteBuildStatus` to tone + label), `Dialog`,
`ConfirmDialog`, `Toast` + `useToast()`, `EmptyState`, `ErrorState` (friendly message +
retry; never raw JSON), `Skeleton` (fixed-size, no layout shift), `Progress`, `Tooltip`,
`Avatar`, `Table` (responsive: stacks into cards below 640px), `Markdown` (react-markdown
with typography styles, links open in a new tab), `Countdown` (days until a date).
Every interactive component has a visible `focus-visible` ring using `focus-ring`.

### Agent identity

`agents/agentIdentity.ts` mirrors `AGENT_PROFILES` (ADR-0009): display name, lucide icon,
accent token. `AgentAvatar` renders the icon in a tinted circle with an accessible name.
Messages, handoff banners and typing indicators use only this map.

### API client (`api/`)

`types.ts` mirrors ADR-0008/0009/0013/0014/0015/0016/0017 field for field (snake_case kept;
decimals arrive as strings). `client.ts` has one typed function per endpoint in ADR-0017,
parses the error envelope into `ApiError{code, message, status}`. `hooks.ts` wraps them in
React Query (`useCase`, `useMessages`, `usePostMessage`, `useNames`, `useChooseName`,
`useCapTable`, `useDocuments`, `useSignDocument`, `useEditDocument`, `useAudit`, `useWebsite`,
`useBuildWebsite`, `useDeployWebsite`, `useGuide`, `useSetGuideItem`, `useAgents`,
`useCreateCase`, `useCases`); mutations invalidate the case and the affected lists.

### Acting founder

`ActingFounderContext` holds the selected founder id per case (`localStorage`
`launch.founder.<caseId>`, default first founder). Every sign/edit/tick/deploy sends it. The
header shows "Acting as {name}" with a note that there is no real sign-in in this release.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| A. Shell + tokens + components + client first, features in isolated folders (chosen) | Five feature tickets in parallel without collisions; consistent look | Wave-1 ticket is large |
| B. Each feature brings its own components | No up-front work | Inconsistent UI; duplicated code; violates "no ad-hoc styling" |
| C. CSS-in-JS theme | Dynamic themes | Extra dependency; fights Tailwind |

## Consequences

- A feature that needs a new shared component reports `BLOCKED`; the Supervisor decides
  whether it goes in a follow-up design-system ticket.
- Copy guidelines: sentence case, plain words, every error says what happened and what to do.
