# ADR-0009: Agent message and handoff protocol

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-23 |
| **Deciders** | Supervisor |
| **Tickets** | T-001 (types), T-006..T-010 (specialists), T-012 (Manager + graph), T-014 (applies actions), T-018 (chat UI) |
| **Scope** | `launch_agents/domain/messages.py`, `launch_agents/agents/base.py`, `launch_agents/orchestrator/` |

## Context

The founder talks to one Manager Agent, which brings in specialists. Specialists speak in
the same conversation and the founder must always see who is speaking and when the
conversation changed hands. Specialists are built in parallel (wave 1) before the Manager
(wave 2), so the way they are called, what they return and how handovers are recorded
must be fixed now. Agents must also stay free of database and HTTP code so they are
testable with fakes.

## Decision

### Who can speak

```python
class AgentId(str, Enum):
    MANAGER = "manager"; LAW = "law"; NAME = "name"; WEBSITE = "website"
    QA = "qa"; GUIDE = "guide"; CAP_TABLE = "cap_table"; SIGNOFF = "signoff"

class AgentProfile(BaseModel):
    id: AgentId; display_name: str; short_name: str
    kind: Literal["llm", "deterministic"]; icon: str   # lucide icon name
    accent: str                                       # design token name (ADR-0019)
    routable: bool                                    # can the Manager hand the chat to it?
```

`AGENT_PROFILES` (binding values):

| id | display_name | short | kind | icon | accent | routable |
|---|---|---|---|---|---|---|
| manager | Manager | Manager | llm | `briefcase` | `agent-manager` | — (always present) |
| law | Law Agent | Law | llm | `scale` | `agent-law` | yes |
| name | Name Agent | Names | llm | `tag` | `agent-name` | yes |
| website | Website Agent | Website | llm | `globe` | `agent-website` | yes |
| qa | QA Agent | QA | llm | `shield-check` | `agent-qa` | no (called by the website pipeline) |
| guide | Registration Guide Agent | Guide | llm | `list-checks` | `agent-guide` | yes |
| cap_table | Cap Table Builder | Cap table | deterministic | `pie-chart` | `agent-cap-table` | no |
| signoff | Sign-off | Sign-off | deterministic | `pen-line` | `agent-signoff` | no |

### Messages

```python
class MessageRole(str, Enum): FOUNDER = "founder"; AGENT = "agent"; SYSTEM = "system"
class MessageKind(str, Enum):
    TEXT = "text"; HANDOFF = "handoff"; NOTICE = "notice"; VALIDATION = "validation"
    NAME_OPTIONS = "name_options"; DOCUMENTS_READY = "documents_ready"
    CAP_TABLE_READY = "cap_table_ready"; SITE_PREVIEW = "site_preview"
    QA_REPORT = "qa_report"; DEPLOY_STATUS = "deploy_status"; GUIDE_READY = "guide_ready"

class SuggestedReply(BaseModel): label: str; text: str

class ChatMessage(BaseModel):
    id: str | None = None            # set by the repository
    case_id: str | None = None
    seq: int | None = None           # 1, 2, 3 ... per case, set by the repository
    role: MessageRole
    agent: AgentId | None = None     # REQUIRED when role == AGENT; None otherwise
    founder_id: str | None = None    # who typed it, when role == FOUNDER
    kind: MessageKind = MessageKind.TEXT
    content: str                     # plain text with light markdown (**bold**, lists, links)
    payload: dict[str, Any] = {}     # kind-specific, see table
    suggested_replies: list[SuggestedReply] = []
    created_at: datetime | None = None
```

A model validator rejects `role == AGENT` without `agent`. Payloads:

| kind | payload |
|---|---|
| handoff | `{"from": AgentId, "to": AgentId, "direction": "handover" \| "return", "reason": str}` |
| validation | `{"issues": [{"code", "field", "message", "founder_id"}]}` (ADR-0013) |
| name_options | `{"candidates": [NameCandidate]}` |
| documents_ready / cap_table_ready / guide_ready | `{"count": int}` and `{"view": "legal" \| "cap_table" \| "guide"}` |
| site_preview | `{"build_id": str, "version": int}` |
| qa_report | `{"build_id": str, "round": int, "passed": bool, "issue_count": int}` |
| deploy_status | `{"build_id": str, "status": SiteBuildStatus, "url": str \| None}` |

Helpers in `domain/messages.py` (implemented in T-001):

```python
def agent_message(agent: AgentId, content: str, *, kind: MessageKind = MessageKind.TEXT,
                  payload: dict | None = None,
                  suggested_replies: list[SuggestedReply] | None = None) -> ChatMessage
def handoff_message(frm: AgentId, to: AgentId, *, direction: Literal["handover", "return"],
                    reason: str) -> ChatMessage
```

`handoff_message` content is fixed wording: handover -> `"Manager brought in the Law Agent"`
(`"{from display} brought in the {to display}"`); return -> `"Law Agent handed the
conversation back to the Manager"`. It is spoken by the `from` agent with kind `handoff`.

### Actions (side effects agents request, executed by `CaseService`, ADR-0017)

```python
class LockFacts(BaseModel):      type: Literal["lock_facts"] = "lock_facts"
class ChooseName(BaseModel):     type: Literal["choose_name"] = "choose_name"; name: str; domain: str | None = None
class DraftDocuments(BaseModel): type: Literal["draft_documents"] = "draft_documents"
class BuildWebsite(BaseModel):   type: Literal["build_website"] = "build_website"; change_request: str | None = None
class DeployWebsite(BaseModel):  type: Literal["deploy_website"] = "deploy_website"; override_qa: bool = False
class OpenView(BaseModel):       type: Literal["open_view"] = "open_view"
                                 view: Literal["overview","names","legal","cap_table","website","guide","audit"]
AgentAction = Annotated[LockFacts | ChooseName | DraftDocuments | BuildWebsite | DeployWebsite | OpenView,
                        Field(discriminator="type")]
```

Agents never perform these effects themselves; they return them.

### Specialist contract (`agents/base.py`)

```python
@dataclass(frozen=True)
class AgentServices:
    domain_checker: DomainChecker          # ADR-0011

@dataclass(frozen=True)
class AgentContext:
    case_id: str
    facts: CaseFacts
    state: CaseState
    history: list[ChatMessage]             # last 20 messages, oldest first, excluding founder_text
    founder_text: str
    founder_id: str | None
    today: date
    llm: LLMProvider                       # ADR-0010
    services: AgentServices

class AgentReply(BaseModel):
    messages: list[ChatMessage] = []       # every message has role=AGENT and agent=<this agent>
    facts_patch: FactsPatch | None = None
    state: CaseState | None = None         # full replacement of CaseState when not None
    actions: list[AgentAction] = []
    hand_back: bool = False                # task done; return the chat to the Manager

class Specialist(Protocol):
    agent_id: AgentId
    def handle(self, ctx: AgentContext) -> AgentReply: ...
```

Every specialist module exports a class implementing `Specialist` with a no-argument
constructor: `LawAgent`, `NameAgent`, `WebsiteAgent`, `GuideAgent`. A specialist must
return at least one message, must never raise for LLM failures (it catches
`LLMOutputError` and replies with a friendly apology), and must keep its text free of
raw JSON.

### The turn (types in `agents/base.py` by T-001; `handle_turn` in `orchestrator/` by T-012)

```python
class TurnInput(BaseModel):
    case_id: str; facts: CaseFacts; state: CaseState
    history: list[ChatMessage]; founder_text: str; founder_id: str | None; today: date
class TurnResult(BaseModel):
    messages: list[ChatMessage]            # new agent messages in order (not the founder's)
    facts: CaseFacts; state: CaseState; actions: list[AgentAction]
@dataclass(frozen=True)
class AgentDeps:
    llm: LLMProvider; services: AgentServices
    specialists: Mapping[AgentId, Specialist] | None = None   # None -> the four real ones
TurnHandler = Callable[[TurnInput, AgentDeps], TurnResult]
def handle_turn(turn: TurnInput, deps: AgentDeps) -> TurnResult: ...
```

`handle_turn` runs a compiled LangGraph `StateGraph` with these nodes, in order:

1. **extract** (Manager): LLM task `manager.extract` -> `ManagerExtraction{facts: FactsPatch,
   confirms_summary: bool}`; `apply_patch`; if facts changed while `facts_locked`, set
   `facts_locked = False` (the Manager says documents will be refreshed after re-confirmation).
2. **validate** (deterministic, `rules.validation`): vesting defaults, issues, missing facts.
3. **route** (Manager): a leading `@law`, `@name`, `@website`, `@guide` or `@manager`
   forces the target. Otherwise LLM task `manager.route` -> `RouteDecision{target: AgentId,
   reason: str}` with the active agent and the last messages in context. A non-routable
   or unknown target becomes `manager`.
4. **handover**: if `target != state.active_agent`: when the active agent is a specialist,
   emit a `return` handoff (specialist -> Manager); when the target is a specialist, emit
   a `handover` handoff (Manager -> target) with the route reason. Set `active_agent`.
5. **respond**: the target runs exactly once. The Manager replies itself when the target is
   `manager` (validation issues first, then the next missing fact, then a summary to
   confirm; on `confirms_summary` with valid complete facts it returns `LockFacts`).
6. **hand_back**: if the specialist returned `hand_back=True`, emit a `return` handoff and
   set `active_agent = manager`.

So each turn calls at most one specialist and emits at most two handoff messages. The
Manager is the only router; specialists never route to each other. Validation is never
done by the LLM.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| A. Manager routes every turn; specialists return messages + actions (chosen) | One router to test; agents pure and fakeable; handovers explicit | Two Manager LLM calls per turn (extract, route) |
| B. Active specialist keeps the chat until it decides to release it | Fewer LLM calls | Specialists must detect out-of-scope questions; hard to test |
| C. LangGraph multi-agent with tools/`Command` handoffs | Idiomatic for the library | Side effects hidden inside the graph; less deterministic |

## Consequences

- The chat UI can render identity and handovers from `agent` and `kind` alone.
- Specialists in wave 1 are tested by building an `AgentContext` with `FakeLLM`.
- New agent kinds or actions require a superseding ADR (they touch the UI, service and graph).
