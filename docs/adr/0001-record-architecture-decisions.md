# ADR-0001: Record architecture decisions

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-23 |
| **Deciders** | Harness operator |
| **Tickets** | — |
| **Scope** | Whole repository |

## Context

This codebase is built by several AI agents working in parallel: a Supervisor that plans,
five or more Builders that each own one ticket, and a Reviewer. No agent keeps memory
between sessions, and Builders see only their own ticket. Without a shared, durable record
of *why* the code is shaped the way it is, each new session either re-decides things
(and drifts) or blindly follows patterns it doesn't understand.

Human teams on large and enterprise codebases have the same problem. Architecture
Decision Records (Michael Nygard's format, described by Martin Fowler at
https://martinfowler.com/bliki/ArchitectureDecisionRecord.html) solve it with short,
numbered documents, one per significant decision, kept in the repository next to the code.

## Decision

We will keep ADRs in `docs/adr/`, numbered `NNNN-kebab-title.md`, using
[0000-template.md](0000-template.md), and list them in [README.md](README.md).

ADRs are part of every stage of delivery, not an afterthought:

| Stage | Who | ADR duty |
|---|---|---|
| Plan | Supervisor | Writes an ADR for each architecture decision before ticketing (stack, module layout, contracts, data model, cross-cutting rules). Every ticket links the ADRs it must follow. |
| Build | Builder | Follows the linked ADRs. If the ticket forces a new significant decision, the Builder writes a `Proposed` ADR in the same PR, or reports `BLOCKED` to the Supervisor when the decision crosses ticket boundaries. |
| Review | Reviewer | Checks the diff against every linked ADR. A violation is a blocking finding. A significant decision made without an ADR is also a blocking finding. |
| Unblock | Supervisor | Answers a blocked Builder with a decision; a decision that affects more than one ticket becomes a new ADR. |
| Merge | Gate | A PR that adds a `Proposed` ADR may merge only after the Reviewer approves it, at which point its status becomes `Accepted`. |

"Significant" means: hard to reverse, affects more than one module or ticket, chooses
between real alternatives, or adds a dependency.

An accepted ADR is never edited except for its Status line. A changed decision gets a new
ADR that supersedes the old one, so the log keeps the history of the thinking.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| A. ADRs in the repo (chosen) | Versioned with the code; every agent can read them; reviewed in the same PR as the change | Needs discipline to write them |
| B. Decisions in ticket text only | No extra files | Scattered; tickets close; no supersession history |
| C. A single design doc | One place to read | Gets edited in place, so the history of decisions is lost; merge conflicts between parallel builders |

## Consequences

- Agents get the "why" from files, not from memory, so parallel sessions stay consistent.
- Reviewers have an objective standard to review against.
- Writing an ADR costs a few minutes per decision; trivial choices must not get ADRs.
