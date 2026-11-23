# ADR-0021: Settings, environments (APP_ENV) and production guards

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-23 |
| **Deciders** | Supervisor |
| **Tickets** | T-001 (implements), every ticket that reads configuration |
| **Scope** | `launch_agents/config.py`, `.env.example` |

## Context

The product is now sold to founders (brief, "Sellable product"). The same code runs on
a developer's laptop, in tests and recorded runs, in the demo video, and in production.
ADR-0010 defined a small `Settings` model for LLM, hosting and the database only. We now
need accounts, email, payments, jobs, security limits and a demo mode, and some
combinations must be impossible in production (a subscription-login LLM, fake payments,
demo "act as founder"). This ADR **supersedes the `Settings` / configuration part of
ADR-0010** (the LLM interface, fake and task catalog in ADR-0010 stay in force; LLM
provider selection is ADR-0022).

## Decision

### Environments

```python
class AppEnv(str, Enum):
    DEVELOPMENT = "development"   # default
    TEST = "test"                 # pytest, recorded runs, the reliable demo
    PRODUCTION = "production"     # the app served to founders
```

`APP_ENV` selects it. Every other setting comes from environment variables (and a `.env`
file via python-dotenv in development only). Nothing secret is ever in code, in
`.env.example`, in an API response or in a log line.

### The settings model (`launch_agents/config.py`, T-001)

```python
class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)
    app_env: AppEnv = AppEnv.DEVELOPMENT
    app_base_url: str = "http://localhost:8000"     # APP_BASE_URL: links in emails, Stripe redirects
    brand_name: str = BRAND_NAME                    # BRAND_NAME (ADR-0035), default from domain.constants
    secret_key: str | None = None                   # SECRET_KEY: HMAC for CSRF and tokens
    demo_mode: bool = False                         # DEMO_MODE=1: "act as founder" + test checkout page
    fake_services: bool = False                     # LAUNCH_FAKE_SERVICES=1 (ADR-0011): fakes for every port
    today: date | None = None                       # LAUNCH_TODAY: fixes "today" for recorded runs
    # LLM (ADR-0022)
    llm_provider: Literal["fake", "claude_code", "anthropic", "deepseek", "groq", "openai-compatible"]
    llm_model: str | None = None                    # LLM_MODEL: default model for the provider
    llm_models: dict[str, str] = {}                 # LLM_MODEL_<AGENT>, e.g. LLM_MODEL_QA=claude-haiku-5-5
    llm_effort: str = "medium"                      # LLM_EFFORT (anthropic only)
    llm_efforts: dict[str, str] = {}                # LLM_EFFORT_<AGENT>
    llm_timeout_s: float = 60
    llm_max_retries: int = 2
    anthropic_api_key: str | None = None; deepseek_api_key: str | None = None
    groq_api_key: str | None = None; llm_api_key: str | None = None; llm_base_url: str | None = None
    anthropic_refusal_fallback: bool = True         # ANTHROPIC_REFUSAL_FALLBACK (ADR-0022)
    claude_code_path: str | None = None             # CLAUDE_CODE_PATH
    claude_code_timeout_s: float = 120
    # external services (ADR-0011, ADR-0029, ADR-0030)
    domain_checker: Literal["rdap", "fake"] = "rdap"
    hosting_provider: Literal["netlify", "fake", "none"] = "none"
    netlify_auth_token: str | None = None
    email_provider: Literal["smtp", "console", "fake"] = "console"
    email_from: str = "no-reply@localhost"          # EMAIL_FROM
    email_drop_file: str | None = None              # EMAIL_DROP_FILE: JSONL mailbox for test/demo runs (ADR-0029)
    smtp_host: str | None = None; smtp_port: int = 587; smtp_username: str | None = None
    smtp_password: str | None = None; smtp_starttls: bool = True
    payments_provider: Literal["stripe", "fake"] = "fake"
    stripe_secret_key: str | None = None; stripe_webhook_secret: str | None = None
    stripe_price_launch_monthly: str | None = None; stripe_price_launch_yearly: str | None = None
    # data and jobs (ADR-0027, ADR-0028)
    db_url: str = "sqlite:///./launch_agents.db"    # LAUNCH_DB_URL (DATABASE_URL also accepted)
    jobs_embedded_worker: bool = True               # JOBS_EMBEDDED_WORKER; default False in production
    # security and operations (ADR-0033, ADR-0034)
    session_idle_days: int = 7; session_max_days: int = 30
    cors_origins: list[str] = ["http://localhost:5173"]   # LAUNCH_CORS_ORIGINS, comma separated
    trusted_proxy_count: int = 0                    # TRUSTED_PROXY_COUNT: hops of X-Forwarded-For to trust
    rate_limits_enabled: bool = True                # RATE_LIMITS_ENABLED (tests may turn off)
    log_format: Literal["json", "text"] = "text"    # LOG_FORMAT; json in production
    log_level: str = "INFO"
    error_reporter: str | None = None               # ERROR_REPORTER="package.module:function"
    frontend_dist: str = "frontend/dist"

    @property
    def is_production(self) -> bool: ...
    def model_for(self, task: str) -> str | None: ...    # agent = task.split(".")[0]; llm_models[agent] or llm_model
    def effort_for(self, task: str) -> str: ...

class ConfigError(Exception):            # startup only; never reaches an HTTP response
    problems: list[str]

def load_settings(env: Mapping[str, str] | None = None) -> Settings: ...   # None -> os.environ (+ .env outside production)
```

`LAUNCH_FAKE_SERVICES=1` (or `APP_ENV=test` with no explicit choice) forces the fake LLM,
fake domain checker, fake host, fake email sender and fake payment gateway; an explicitly
set `HOSTING_PROVIDER` still wins for hosting (ADR-0011). Defaults per environment:

| Setting | development | test | production |
|---|---|---|---|
| `email_provider` | `console` (prints the email and its link) | `fake` | must be `smtp` |
| `payments_provider` | `fake` unless `STRIPE_SECRET_KEY` set | `fake` | must be `stripe` |
| `jobs_embedded_worker` | `True` | `True` (tests use `InlineJobRunner`) | `False` (separate worker) |
| `log_format` | `text` | `text` | `json` |
| `secret_key` | fixed insecure dev value + startup warning | fixed test value | required, >= 32 chars |

### Production guards

`load_settings` collects every problem and raises one `ConfigError` listing them all
when `APP_ENV=production` and any of these hold:

- `llm_provider` is `fake` or `claude_code` (claude_code: Anthropic's terms allow a
  subscription login only for the owner's own use, never for serving other users);
- the chosen LLM provider has no API key;
- `fake_services` or `demo_mode` is on, or `EMAIL_DROP_FILE` is set;
- `payments_provider != "stripe"` or a Stripe key, webhook secret or price id is missing;
- `email_provider != "smtp"` or `smtp_host` / `email_from` is missing;
- `secret_key` is missing or shorter than 32 characters;
- `db_url` is not PostgreSQL (`postgresql+psycopg://...`);
- `app_base_url` is not `https://`, or `cors_origins` contains `*` or a non-https origin.

`demo_mode` is also refused unless `fake_services` is on or `APP_ENV != production`
(so a real customer's data can never be acted on "as another founder").

`.env.example` (T-001) lists every variable above with a one-line comment, grouped by
environment, with no real values.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| A. One frozen pydantic `Settings`, `APP_ENV`, fail-fast production guards (chosen) | Misconfiguration found at start-up, not by a customer; one place to read | Long model |
| B. Separate settings classes per environment | Smaller classes | Easy to forget a guard in one class |
| C. Feature flags in the database | Change at runtime | Secrets and providers must not be runtime-editable |

## Consequences

- Production can only start with real, API-key based services; the policy that
  `claude_code` is for the owner's own machine is enforced by code, not by memory.
- Tests build settings with `load_settings({...})` maps; no test reads the real environment.
- Adding a setting is additive (no superseding ADR) when it has a safe default.
