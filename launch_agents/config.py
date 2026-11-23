"""Settings, environments and production guards (ADR-0021, ADR-0022, ADR-0038).

Tests build settings with ``load_settings({...})`` maps; no test reads the real environment.
Nothing secret is ever printed: ``repr(settings)`` redacts every field whose name contains
``key``, ``secret``, ``token`` or ``password`` (ADR-0033).
"""

from __future__ import annotations

import logging
import os
from datetime import date
from enum import Enum
from typing import Any, Literal, Mapping

from pydantic import BaseModel, ConfigDict, ValidationError

from .domain.billing import DEFAULT_PLAN_AMOUNTS, Plan, PlanAmounts, PlanId, build_plans
from .domain.constants import BRAND_NAME

__all__ = ["AppEnv", "ConfigError", "LLM_PROVIDERS", "Settings", "load_settings"]

log = logging.getLogger(__name__)

LLM_PROVIDERS = ("fake", "claude_code", "anthropic", "deepseek", "groq", "openai-compatible")
_SECRET_MARKERS = ("key", "secret", "token", "password")
_DEV_SECRET_KEY = "dev-insecure-secret-key-change-me-0123456789"  # >= 32 chars, development only
_TEST_SECRET_KEY = "test-secret-key-not-for-production-0123456789"
_SQLITE_DEFAULT = "sqlite:///./launch_agents.db"
_warned_dev_secret = False  # the development-key warning is logged once per process


class AppEnv(str, Enum):
    DEVELOPMENT = "development"  # default
    TEST = "test"  # pytest, recorded runs, the reliable demo
    PRODUCTION = "production"  # the app served to founders


class ConfigError(Exception):
    """Invalid configuration, raised at start-up only; never reaches an HTTP response."""

    def __init__(self, problems: list[str] | str) -> None:
        self.problems: list[str] = [problems] if isinstance(problems, str) else list(problems)
        lines = "\n".join(f"- {p}" for p in self.problems)
        super().__init__(f"Configuration problems ({len(self.problems)}):\n{lines}")


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)

    app_env: AppEnv = AppEnv.DEVELOPMENT
    app_base_url: str = "http://localhost:8000"  # APP_BASE_URL: links in emails, Stripe redirects
    brand_name: str = BRAND_NAME  # BRAND_NAME (ADR-0039)
    secret_key: str | None = None  # SECRET_KEY: HMAC for CSRF and tokens
    demo_mode: bool = False  # DEMO_MODE=1: "act as founder" + test checkout page
    fake_services: bool = False  # LAUNCH_FAKE_SERVICES=1 (ADR-0011): fakes for every port
    today: date | None = None  # LAUNCH_TODAY: fixes "today" for recorded runs
    # LLM (ADR-0022)
    llm_provider: Literal["fake", "claude_code", "anthropic", "deepseek", "groq", "openai-compatible"] = "fake"
    llm_model: str | None = None  # LLM_MODEL: default model for the provider
    llm_models: dict[str, str] = {}  # LLM_MODEL_<AGENT>, e.g. LLM_MODEL_QA=claude-haiku-5-5
    llm_effort: str = "medium"  # LLM_EFFORT (anthropic only)
    llm_efforts: dict[str, str] = {}  # LLM_EFFORT_<AGENT>
    llm_timeout_s: float = 60
    llm_max_retries: int = 2
    anthropic_api_key: str | None = None
    deepseek_api_key: str | None = None
    groq_api_key: str | None = None
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    anthropic_refusal_fallback: bool = True  # ANTHROPIC_REFUSAL_FALLBACK (ADR-0022)
    claude_code_path: str | None = None  # CLAUDE_CODE_PATH
    claude_code_timeout_s: float = 120
    # external services (ADR-0011, ADR-0029, ADR-0030)
    domain_checker: Literal["rdap", "fake"] = "rdap"
    hosting_provider: Literal["netlify", "fake", "none"] = "none"
    netlify_auth_token: str | None = None
    email_provider: Literal["smtp", "console", "fake"] = "console"
    email_from: str = "no-reply@localhost"  # EMAIL_FROM
    email_drop_file: str | None = None  # EMAIL_DROP_FILE: JSONL mailbox for test/demo runs
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_starttls: bool = True
    payments_provider: Literal["stripe", "fake"] = "fake"
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    stripe_price_launch_monthly: str | None = None
    stripe_price_launch_yearly: str | None = None
    # billing (ADR-0038)
    stripe_price_team_monthly: str | None = None
    stripe_price_team_yearly: str | None = None
    billing_yearly_enabled: bool = True
    plan_amounts: dict[PlanId, PlanAmounts] = dict(DEFAULT_PLAN_AMOUNTS)
    support_email: str | None = None
    # data and jobs (ADR-0027, ADR-0028)
    db_url: str = _SQLITE_DEFAULT  # LAUNCH_DB_URL (DATABASE_URL also accepted)
    jobs_embedded_worker: bool = True  # JOBS_EMBEDDED_WORKER; default False in production
    # security and operations (ADR-0033, ADR-0034)
    session_idle_days: int = 7
    session_max_days: int = 30
    cors_origins: list[str] = ["http://localhost:5173"]  # LAUNCH_CORS_ORIGINS, comma separated
    trusted_proxy_count: int = 0  # TRUSTED_PROXY_COUNT
    rate_limits_enabled: bool = True  # RATE_LIMITS_ENABLED
    log_format: Literal["json", "text"] = "text"  # LOG_FORMAT
    log_level: str = "INFO"  # LOG_LEVEL
    error_reporter: str | None = None  # ERROR_REPORTER="package.module:function"
    frontend_dist: str = "frontend/dist"  # FRONTEND_DIST

    @property
    def is_production(self) -> bool:
        return self.app_env == AppEnv.PRODUCTION

    def model_for(self, task: str) -> str | None:
        """Model for an LLM task: ``LLM_MODEL_<AGENT>`` (agent = first task segment), else ``LLM_MODEL``."""
        agent = task.split(".", 1)[0].lower()
        return self.llm_models.get(agent) or self.llm_model

    def effort_for(self, task: str) -> str:
        """Effort for an LLM task: ``LLM_EFFORT_<AGENT>``, else ``LLM_EFFORT``."""
        agent = task.split(".", 1)[0].lower()
        return self.llm_efforts.get(agent) or self.llm_effort

    def plans(self) -> dict[PlanId, Plan]:
        """The plans as configured (ADR-0038): the only source of plans for services."""
        return build_plans(self.plan_amounts, yearly_enabled=self.billing_yearly_enabled)

    def __repr_args__(self):  # type: ignore[override]
        for name, value in super().__repr_args__():
            if name and any(marker in name for marker in _SECRET_MARKERS):
                yield name, ("***" if value else value)
            else:
                yield name, _mask_url_passwords(value)


def _mask_url_password(url: str) -> str:
    """``url`` with the password of a ``scheme://user:password@host`` part replaced by ``***``
    (e.g. ``LAUNCH_DB_URL``, ``LLM_BASE_URL``), for ``repr``/``str`` and log lines (ADR-0021).
    The credentials end at the last ``@`` before any ``?`` or ``#``, so an unencoded ``@`` or
    ``/`` in the password is masked too; anything without credentials is returned unchanged."""
    scheme_end = url.find("://")
    if scheme_end <= 0:
        return url
    start = scheme_end + 3
    stop = len(url)
    for sep in ("?", "#"):
        pos = url.find(sep, start)
        if pos != -1:
            stop = min(stop, pos)
    at = url.rfind("@", start, stop)
    if at == -1:
        return url
    colon = url.find(":", start, at)
    if colon == -1:
        return url
    return f"{url[:colon + 1]}***{url[at:]}"


def _mask_url_passwords(value: Any) -> Any:
    if isinstance(value, str):
        return _mask_url_password(value)
    if isinstance(value, list):
        return [_mask_url_passwords(v) for v in value]
    if isinstance(value, dict):
        return {k: _mask_url_passwords(v) for k, v in value.items()}
    return value


# ---------------------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------------------

_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}

_PLAN_FIELDS = {
    "PRICE_MONTH_CENTS": "price_month_cents",
    "PRICE_YEAR_CENTS": "price_year_cents",
    "MAX_COMPANIES": "max_companies",
    "AI_MESSAGES": "ai_messages_per_month",
}

_API_KEY_FOR_PROVIDER = {
    "anthropic": ("anthropic_api_key", "ANTHROPIC_API_KEY"),
    "deepseek": ("deepseek_api_key", "DEEPSEEK_API_KEY"),
    "groq": ("groq_api_key", "GROQ_API_KEY"),
    "openai-compatible": ("llm_api_key", "LLM_API_KEY"),
}


class _Reader:
    """Reads typed values from an env map, collecting every problem instead of failing fast."""

    def __init__(self, env: Mapping[str, str]) -> None:
        self.env = env
        self.problems: list[str] = []

    def raw(self, name: str) -> str | None:
        value = self.env.get(name)
        if value is None:
            return None
        value = str(value).strip()
        return value if value != "" else None

    def has(self, name: str) -> bool:
        return self.raw(name) is not None

    def text(self, name: str, default: str | None = None) -> str | None:
        value = self.raw(name)
        return default if value is None else value

    def flag(self, name: str, default: bool) -> bool:
        value = self.raw(name)
        if value is None:
            return default
        low = value.lower()
        if low in _TRUE:
            return True
        if low in _FALSE:
            return False
        self.problems.append(f"{name} must be 1/0 (or true/false), got {value!r}.")
        return default

    def integer(self, name: str, default: int) -> int:
        value = self.raw(name)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            self.problems.append(f"{name} must be a whole number, got {value!r}.")
            return default

    def number(self, name: str, default: float) -> float:
        value = self.raw(name)
        if value is None:
            return default
        try:
            return float(value)
        except ValueError:
            self.problems.append(f"{name} must be a number, got {value!r}.")
            return default

    def choice(self, name: str, choices: tuple[str, ...]) -> str | None:
        value = self.raw(name)
        if value is None:
            return None
        if value not in choices:
            self.problems.append(f"{name} must be one of {', '.join(choices)}; got {value!r}.")
            return None
        return value

    def per_agent(self, prefix: str) -> dict[str, str]:
        out: dict[str, str] = {}
        for key in sorted(self.env):
            if key.startswith(prefix) and len(key) > len(prefix):
                value = self.raw(key)
                if value is not None:
                    out[key[len(prefix):].lower()] = value
        return out


def _environment(env: Mapping[str, str] | None) -> Mapping[str, str]:
    if env is not None:
        return env
    merged: dict[str, str] = dict(os.environ)
    if (merged.get("APP_ENV") or "").strip().lower() != AppEnv.PRODUCTION.value:
        try:
            from dotenv import dotenv_values

            for key, value in dotenv_values(".env").items():
                if key not in merged and value is not None:
                    merged[key] = value
        except Exception:  # pragma: no cover - a broken .env must not hide the real error
            log.warning("could not read .env; using the process environment only")
    return merged


def _plan_amounts(r: _Reader) -> dict[PlanId, PlanAmounts]:
    amounts: dict[PlanId, PlanAmounts] = {}
    for plan_id in PlanId:
        base = DEFAULT_PLAN_AMOUNTS[plan_id].model_dump()
        for suffix, field in _PLAN_FIELDS.items():
            name = f"PLAN_{plan_id.value.upper()}_{suffix}"
            value = r.integer(name, base[field])
            if value < 0:
                r.problems.append(f"{name} must not be negative (got {value}).")
            base[field] = value
        amounts[plan_id] = PlanAmounts(**base)
    return amounts


def _select_llm(r: _Reader, *, fake_forced: bool, test_default: bool) -> str:
    explicit = r.choice("LLM_PROVIDER", LLM_PROVIDERS)
    if fake_forced:
        return "fake"
    if explicit is not None:
        return explicit
    if test_default:
        return "fake"
    # ADR-0022: claude_code is never chosen implicitly.
    if r.has("ANTHROPIC_API_KEY"):
        return "anthropic"
    if r.has("DEEPSEEK_API_KEY"):
        return "deepseek"
    if r.has("GROQ_API_KEY"):
        return "groq"
    return "fake"


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    """Build ``Settings`` from an env map (``None`` -> ``os.environ`` plus ``.env`` outside production).

    Applies the per-environment defaults of ADR-0021, the LLM selection of ADR-0022 and, for
    ``APP_ENV=production``, every production guard: all problems are collected and raised
    together as one ``ConfigError``.
    """
    r = _Reader(_environment(env))

    env_name = (r.raw("APP_ENV") or AppEnv.DEVELOPMENT.value).lower()
    try:
        app_env = AppEnv(env_name)
    except ValueError:
        raise ConfigError([f"APP_ENV must be development, test or production; got {env_name!r}."]) from None
    prod = app_env == AppEnv.PRODUCTION
    test = app_env == AppEnv.TEST

    # LAUNCH_FAKE_SERVICES=1 forces every fake; APP_ENV=test with no explicit choice defaults to them.
    fake_forced = r.flag("LAUNCH_FAKE_SERVICES", False)
    test_default = test and not r.has("LAUNCH_FAKE_SERVICES")
    fake_services = fake_forced or test_default

    values: dict[str, Any] = {
        "app_env": app_env,
        "app_base_url": (r.text("APP_BASE_URL", "http://localhost:8000") or "").rstrip("/"),
        "brand_name": r.text("BRAND_NAME", BRAND_NAME),
        "demo_mode": r.flag("DEMO_MODE", False),
        "fake_services": fake_services,
    }

    today = r.raw("LAUNCH_TODAY")
    if today is not None:
        try:
            values["today"] = date.fromisoformat(today)
        except ValueError:
            r.problems.append(f"LAUNCH_TODAY must be a date like 2026-11-23, got {today!r}.")

    # Secret key: fixed values outside production (ADR-0021).
    secret = r.text("SECRET_KEY")
    if secret is None and app_env == AppEnv.DEVELOPMENT:
        secret = _DEV_SECRET_KEY
        global _warned_dev_secret
        if not _warned_dev_secret:
            _warned_dev_secret = True
            log.warning("SECRET_KEY is not set: using an insecure development key. Never use it in production.")
    elif secret is None and test:
        secret = _TEST_SECRET_KEY
    values["secret_key"] = secret

    # LLM (ADR-0022)
    values.update(
        llm_provider=_select_llm(r, fake_forced=fake_forced, test_default=test_default),
        llm_model=r.text("LLM_MODEL"),
        llm_models=r.per_agent("LLM_MODEL_"),
        llm_effort=r.text("LLM_EFFORT", "medium"),
        llm_efforts=r.per_agent("LLM_EFFORT_"),
        llm_timeout_s=r.number("LLM_TIMEOUT_S", 60.0),
        llm_max_retries=r.integer("LLM_MAX_RETRIES", 2),
        anthropic_api_key=r.text("ANTHROPIC_API_KEY"),
        deepseek_api_key=r.text("DEEPSEEK_API_KEY"),
        groq_api_key=r.text("GROQ_API_KEY"),
        llm_api_key=r.text("LLM_API_KEY"),
        llm_base_url=r.text("LLM_BASE_URL"),
        anthropic_refusal_fallback=r.flag("ANTHROPIC_REFUSAL_FALLBACK", True),
        claude_code_path=r.text("CLAUDE_CODE_PATH"),
        claude_code_timeout_s=r.number("CLAUDE_CODE_TIMEOUT_S", 120.0),
    )

    # Domain checks and hosting (ADR-0011): an explicit HOSTING_PROVIDER always wins.
    explicit_checker = r.choice("DOMAIN_CHECKER", ("rdap", "fake"))
    if fake_forced:
        values["domain_checker"] = "fake"
    else:
        values["domain_checker"] = explicit_checker or ("fake" if test_default else "rdap")
    netlify_token = r.text("NETLIFY_AUTH_TOKEN")
    explicit_host = r.choice("HOSTING_PROVIDER", ("netlify", "fake", "none"))
    if explicit_host is not None:
        values["hosting_provider"] = explicit_host
    elif fake_services:
        values["hosting_provider"] = "fake"
    else:
        values["hosting_provider"] = "netlify" if netlify_token else "none"
    values["netlify_auth_token"] = netlify_token

    # Email (ADR-0029)
    explicit_email = r.choice("EMAIL_PROVIDER", ("smtp", "console", "fake"))
    if fake_forced:
        values["email_provider"] = "fake"
    elif explicit_email is not None:
        values["email_provider"] = explicit_email
    else:
        values["email_provider"] = "smtp" if prod else ("fake" if test else "console")
    values.update(
        email_from=r.text("EMAIL_FROM", "no-reply@localhost"),
        email_drop_file=r.text("EMAIL_DROP_FILE"),
        smtp_host=r.text("SMTP_HOST"),
        smtp_port=r.integer("SMTP_PORT", 587),
        smtp_username=r.text("SMTP_USERNAME"),
        smtp_password=r.text("SMTP_PASSWORD"),
        smtp_starttls=r.flag("SMTP_STARTTLS", True),
    )

    # Payments (ADR-0030, ADR-0038)
    stripe_key = r.text("STRIPE_SECRET_KEY")
    explicit_payments = r.choice("PAYMENTS_PROVIDER", ("stripe", "fake"))
    if fake_forced:
        values["payments_provider"] = "fake"
    elif explicit_payments is not None:
        values["payments_provider"] = explicit_payments
    elif prod:
        values["payments_provider"] = "stripe"
    elif test:
        values["payments_provider"] = "fake"
    else:
        values["payments_provider"] = "stripe" if stripe_key else "fake"
    values.update(
        stripe_secret_key=stripe_key,
        stripe_webhook_secret=r.text("STRIPE_WEBHOOK_SECRET"),
        stripe_price_launch_monthly=r.text("STRIPE_PRICE_LAUNCH_MONTHLY"),
        stripe_price_launch_yearly=r.text("STRIPE_PRICE_LAUNCH_YEARLY"),
        stripe_price_team_monthly=r.text("STRIPE_PRICE_TEAM_MONTHLY"),
        stripe_price_team_yearly=r.text("STRIPE_PRICE_TEAM_YEARLY"),
        billing_yearly_enabled=r.flag("BILLING_YEARLY_ENABLED", True),
        plan_amounts=_plan_amounts(r),
        support_email=r.text("SUPPORT_EMAIL"),
    )

    # Data, jobs, security, operations
    cors = r.raw("LAUNCH_CORS_ORIGINS")
    values.update(
        db_url=r.text("LAUNCH_DB_URL") or r.text("DATABASE_URL") or _SQLITE_DEFAULT,
        jobs_embedded_worker=r.flag("JOBS_EMBEDDED_WORKER", not prod),
        session_idle_days=r.integer("SESSION_IDLE_DAYS", 7),
        session_max_days=r.integer("SESSION_MAX_DAYS", 30),
        cors_origins=[o.strip().rstrip("/") for o in cors.split(",") if o.strip()] if cors else ["http://localhost:5173"],
        trusted_proxy_count=r.integer("TRUSTED_PROXY_COUNT", 0),
        rate_limits_enabled=r.flag("RATE_LIMITS_ENABLED", True),
        log_format=r.choice("LOG_FORMAT", ("json", "text")) or ("json" if prod else "text"),
        log_level=(r.text("LOG_LEVEL", "INFO") or "INFO").upper(),
        error_reporter=r.text("ERROR_REPORTER"),
        frontend_dist=r.text("FRONTEND_DIST", "frontend/dist"),
    )

    if r.problems:
        raise ConfigError(r.problems)
    try:
        settings = Settings(**values)
    except ValidationError as exc:  # pragma: no cover - values are checked above
        raise ConfigError([f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()]) from None

    problems = _production_problems(settings) if prod else []
    if problems:
        raise ConfigError(problems)
    return settings


def _production_problems(s: Settings) -> list[str]:
    """Every reason this configuration must not serve founders (ADR-0021, ADR-0038)."""
    p: list[str] = []
    # LLM
    if s.llm_provider == "claude_code":
        p.append(
            "LLM_PROVIDER=claude_code is not allowed in production: it uses a personal Claude Code login, "
            "which Anthropic's terms allow only for your own local development. Use LLM_PROVIDER=anthropic "
            "with ANTHROPIC_API_KEY."
        )
    elif s.llm_provider == "fake":
        p.append("LLM_PROVIDER=fake is not allowed in production: set a real provider and its API key.")
    else:
        field, env_name = _API_KEY_FOR_PROVIDER[s.llm_provider]
        if not getattr(s, field):
            p.append(f"{env_name} is required for LLM_PROVIDER={s.llm_provider}.")
        if s.llm_provider == "openai-compatible" and not s.llm_base_url:
            p.append("LLM_BASE_URL is required for LLM_PROVIDER=openai-compatible.")
    # Fakes and demo
    if s.fake_services:
        p.append("LAUNCH_FAKE_SERVICES must be off in production.")
    if s.demo_mode:
        p.append("DEMO_MODE must be off in production (acting as another founder is a demo-only feature).")
    if s.email_drop_file:
        p.append("EMAIL_DROP_FILE must not be set in production.")
    # Payments
    if s.payments_provider != "stripe":
        p.append(f"PAYMENTS_PROVIDER must be stripe in production (got {s.payments_provider}).")
    if not s.stripe_secret_key:
        p.append("STRIPE_SECRET_KEY is required in production.")
    if not s.stripe_webhook_secret:
        p.append("STRIPE_WEBHOOK_SECRET is required in production.")
    price_ids = {
        "STRIPE_PRICE_LAUNCH_MONTHLY": s.stripe_price_launch_monthly,
        "STRIPE_PRICE_TEAM_MONTHLY": s.stripe_price_team_monthly,
    }
    if s.billing_yearly_enabled:
        price_ids["STRIPE_PRICE_LAUNCH_YEARLY"] = s.stripe_price_launch_yearly
        price_ids["STRIPE_PRICE_TEAM_YEARLY"] = s.stripe_price_team_yearly
    for env_name, value in price_ids.items():
        if not value:
            p.append(f"{env_name} is required in production.")
    for plan_id, amounts in s.plan_amounts.items():
        upper = plan_id.value.upper()
        if plan_id == PlanId.FREE:
            if amounts.price_month_cents > 0 or amounts.price_year_cents > 0:
                p.append("The Free plan must cost 0 (PLAN_FREE_PRICE_MONTH_CENTS / PLAN_FREE_PRICE_YEAR_CENTS).")
            continue
        if amounts.price_month_cents <= 0:
            p.append(f"PLAN_{upper}_PRICE_MONTH_CENTS must be above 0 for a paid plan (got {amounts.price_month_cents}).")
        if s.billing_yearly_enabled and amounts.price_year_cents <= 0:
            p.append(f"PLAN_{upper}_PRICE_YEAR_CENTS must be above 0 for a paid plan (got {amounts.price_year_cents}).")
    if not s.support_email:
        p.append("SUPPORT_EMAIL is required in production (the help menu's Contact support).")
    # Email
    if s.email_provider != "smtp":
        p.append(f"EMAIL_PROVIDER must be smtp in production (got {s.email_provider}).")
    if not s.smtp_host:
        p.append("SMTP_HOST is required in production.")
    if not s.email_from or s.email_from.endswith("@localhost"):
        p.append("EMAIL_FROM must be a real sending address in production.")
    # Secrets and data
    if not s.secret_key:
        p.append("SECRET_KEY is required in production (at least 32 characters).")
    elif len(s.secret_key) < 32:
        p.append("SECRET_KEY must be at least 32 characters in production.")
    if not s.db_url.startswith("postgresql+psycopg://"):
        p.append("LAUNCH_DB_URL must be a PostgreSQL URL (postgresql+psycopg://...) in production.")
    # Web
    if not s.app_base_url.startswith("https://"):
        p.append("APP_BASE_URL must start with https:// in production.")
    bad_origins = [o for o in s.cors_origins if o == "*" or not o.startswith("https://")]
    if bad_origins:
        p.append(f"LAUNCH_CORS_ORIGINS must list only https origins in production (no *); got {', '.join(bad_origins)}.")
    return p
