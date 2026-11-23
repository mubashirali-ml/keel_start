# ADR-0010: LLM provider abstraction and deterministic fake

| | |
|---|---|
| **Status** | Partly superseded by ADR-0021 (settings) and ADR-0022 (providers); interface, fake and task catalog still Accepted |
| **Date** | 2026-11-23 |
| **Deciders** | Supervisor |
| **Tickets** | T-001 (implements), all agent tickets (consume and register fake handlers) |
| **Scope** | `launch_agents/llm/`, `launch_agents/config.py`, `launch_agents/agents/*/fake.py` |

## Context

The brief requires OpenAI-compatible providers (DeepSeek primary, Groq for now) chosen
by configuration, with no code change. Tests and recorded runs must be deterministic and
need no key (ADR-0003). Agents need both free text and structured JSON output.

## Decision

### Interface (`llm/provider.py`)

```python
class LLMMessage(BaseModel):
    role: Literal["system", "user", "assistant"]; content: str

class LLMRequest(BaseModel):
    task: str                         # dotted task name from the catalog below
    messages: list[LLMMessage]
    context: dict[str, Any] = {}      # structured inputs; real providers ignore it,
                                      # the fake reads it (the prompt must also contain them)
    temperature: float = 0.2
    max_tokens: int | None = None

T = TypeVar("T", bound=BaseModel)

class LLMProvider(Protocol):
    name: str                         # "deepseek" | "groq" | "openai-compatible" | "fake"
    def complete(self, request: LLMRequest) -> str: ...
    def complete_json(self, request: LLMRequest, schema: type[T]) -> T: ...
```

`complete_json` contract (both implementations): the result is validated with
`schema.model_validate`; on invalid output the real provider retries once with the
validation error appended; a second failure raises `LLMOutputError`. Network/auth errors
raise `LLMOutputError` too. Agents catch it and answer politely (ADR-0009).

### Real provider (`llm/openai_compat.py`)

`OpenAICompatibleProvider(base_url: str, api_key: str, model: str, name: str, timeout_s: float = 60)`
wraps `langchain_openai.ChatOpenAI(base_url=..., api_key=..., model=..., timeout=...)`.
For `complete_json` it appends a system instruction with the JSON schema
(`schema.model_json_schema()`) and requests `response_format={"type": "json_object"}`
(supported by both DeepSeek and Groq), then strips code fences before parsing.

### Configuration (`config.py`, env vars, `.env` loaded by python-dotenv)

| Variable | Meaning | Default |
|---|---|---|
| `LLM_PROVIDER` | `deepseek` \| `groq` \| `openai-compatible` \| `fake` | `deepseek` if `DEEPSEEK_API_KEY` set, else `groq` if `GROQ_API_KEY` set, else `fake` |
| `DEEPSEEK_API_KEY` | key | — |
| `GROQ_API_KEY` | key | — |
| `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL` | override preset values | preset |
| `LLM_TIMEOUT_S` | request timeout | `60` |
| `LAUNCH_FAKE_SERVICES` | `1` forces fake LLM, fake domain checker, fake host | `0` |

Presets: `deepseek` -> `https://api.deepseek.com`, model `deepseek-chat`;
`groq` -> `https://api.groq.com/openai/v1`, model `llama-3.3-70b-versatile`.

```python
class Settings(BaseModel):
    llm_provider: str; llm_base_url: str | None; llm_api_key: str | None; llm_model: str | None
    llm_timeout_s: float = 60
    domain_checker: Literal["rdap", "fake"] = "rdap"                 # ADR-0011
    hosting_provider: Literal["netlify", "fake", "none"] = "none"    # ADR-0011
    netlify_auth_token: str | None = None
    db_url: str = "sqlite:///./launch_agents.db"                     # ADR-0012
    fake_services: bool = False
    today: date | None = None          # LAUNCH_TODAY, fixes "today" for recorded runs
    cors_origins: list[str] = ["http://localhost:5173"]
    frontend_dist: str = "frontend/dist"
def load_settings(env: Mapping[str, str] | None = None) -> Settings: ...   # None -> os.environ (+ .env)
def get_llm(settings: Settings) -> LLMProvider: ...                         # in llm/__init__.py
```

### Deterministic fake (`llm/fake.py`)

```python
FakeHandler = Callable[[LLMRequest], str | dict | BaseModel]
class FakeLLMMissingHandler(LookupError): ...
class FakeLLM:
    name = "fake"
    def __init__(self, handlers: Mapping[str, FakeHandler] | None = None, *, include_defaults: bool = True): ...
    def register(self, task: str, handler: FakeHandler) -> None: ...
    def script(self, task: str, responses: Sequence[str | dict | BaseModel]) -> None: ...
    calls: list[LLMRequest]           # every request, in order
```

Resolution order per request: a queued `script` response for that task (FIFO), else an
explicitly registered handler, else a default handler, else raise `FakeLLMMissingHandler`
(tests fail loudly rather than receive silent junk). `complete_json` validates the fake's
output against the schema exactly like the real provider (invalid fake output raises
`LLMOutputError`, which lets tests exercise the error path). Handlers must be pure
functions of the request: same request, same answer.

**Default handlers** are collected from each agent package's `fake.py`, which exports
`FAKE_HANDLERS: dict[str, FakeHandler]` for that agent's tasks only. `llm/fake.py` lists
the modules (`launch_agents.agents.{manager,law,name,website,qa,guide}.fake`) and imports
them lazily; T-001 creates each with an empty dict and the agent ticket fills it. The
defaults must make the demo journey (ADR-0020) read naturally: they derive answers from
`request.context` (e.g. the Name fake builds names from the business description), not
from canned strings unrelated to the case.

### Task catalog (task name -> output)

| Task | Owner | Output |
|---|---|---|
| `manager.extract` | T-012 | JSON `ManagerExtraction` |
| `manager.route` | T-012 | JSON `RouteDecision` |
| `manager.reply` | T-012 | text (small talk / general answers) |
| `law.answer` | T-006 | text |
| `law.intent` | T-006 | JSON `LawIntent{intent: "question" \| "draft_documents", topic: str \| None}` |
| `name.intent` | T-007 | JSON `NameIntent{intent: "suggest" \| "choose" \| "check" \| "question", name: str \| None, index: int \| None}` |
| `name.suggest` | T-007 | JSON `NameSuggestions{names: list[NameSuggestion]}` |
| `name.reply` | T-007 | text |
| `website.intent` | T-008 | JSON `WebsiteIntent{intent: "build" \| "change" \| "deploy" \| "question", change_request: str \| None, override_qa: bool, requirements: WebsitePatch \| None}` |
| `website.reply` | T-008 | text |
| `website.generate` / `website.revise` / `website.fix` | T-008 | JSON `SiteContent` (ADR-0015) |
| `qa.review` | T-009 | JSON `QaLlmReview{issues: list[QaIssue]}` |
| `guide.explain` | T-010 | text |

Each task's request puts its inputs into `context` with the keys documented in the owning
ticket. Prompts live next to the agent (`agents/<name>/prompts.py`).

## Options considered

| Option | Pros | Cons |
|---|---|---|
| A. Own small interface over `ChatOpenAI`, task-keyed fake (chosen) | Provider switch by env; tests deterministic; fake output validated like real output | Each agent maintains fake handlers |
| B. LangChain `FakeListChatModel` | Built in | Order-dependent canned replies; brittle when the call order changes |
| C. Record/replay real responses | Realistic | Needs keys to record; fixtures go stale |

## Consequences

- No test or recorded run needs a key. A live-provider run is optional extra evidence.
- Agents must put every input they use into `context` so the fake can be honest.
