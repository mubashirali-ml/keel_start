"""Helpers for browser-driven UI recorded runs (ADR-0005, ADR-0036). Owned by T-011.

A UI ticket's ``evidence/T-NNN/feature_run.py`` typically does::

    dist = build_frontend()
    with running_app(seed_stage="legal") as app, sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        login(page, app)                       # through the real login form
        ...                                    # drive the flow, assert visible text
        assert_no_horizontal_scroll(page); assert_no_raw_json(page)
        capture_matrix(browser, app.base_url + "/app", "companies", EVIDENCE)

Playwright types are imported for annotations only, so this module imports without a browser.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Iterator, Mapping

if TYPE_CHECKING:  # pragma: no cover
    from playwright.sync_api import Browser, Page

__all__ = [
    "DEMO_PASSWORD",
    "DEMO_TODAY",
    "DEVICES",
    "THEMES",
    "RunningApp",
    "assert_no_horizontal_scroll",
    "assert_no_raw_json",
    "build_frontend",
    "capture_matrix",
    "compose_env",
    "find_free_port",
    "find_raw_json",
    "frontend_is_stale",
    "login",
    "running_app",
    "screenshot_name",
    "wait_for_ready",
]

DEMO_TODAY = date(2026, 11, 23)
DEMO_PASSWORD = "demo-password-2026"  # only ever used with fake services

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = REPO_ROOT / "frontend"
BUILD_STAMP = ".ui-run-build"  # written into dist/ by build_frontend
READY_TIMEOUT_S = 30.0
MAX_SCREENSHOT_BYTES = 500_000  # ADR-0036: each PNG < 500 KB

# Screenshot matrix (ADR-0005): desktop 1280px and phone 390px, light and dark.
DEVICES: dict[str, dict[str, int]] = {"desktop": {"width": 1280, "height": 800}, "phone": {"width": 390, "height": 844}}
THEMES = ("light", "dark")

# Inherited variables that would change how the app under test behaves; a run is hermetic.
_INHERITED_PREFIXES = (
    "APP_", "LAUNCH_", "DATABASE_URL", "DEMO_MODE", "EMAIL_", "SMTP_", "STRIPE_", "PAYMENTS_", "LLM_",
    "ANTHROPIC_", "DEEPSEEK_", "GROQ_", "NETLIFY_", "HOSTING_", "SECRET_KEY", "SUPPORT_EMAIL", "FRONTEND_DIST",
    "RATE_LIMITS_ENABLED", "JOBS_EMBEDDED_WORKER", "BILLING_", "PLAN_", "BRAND_NAME", "DOMAIN_CHECKER",
    "CLAUDE_CODE_", "SESSION_", "TRUSTED_PROXY_COUNT", "LOG_", "ERROR_REPORTER",
)


@dataclass
class RunningApp:
    base_url: str
    db_url: str
    case_id: str | None
    users: dict[str, str]  # "alice" -> email, "bob" -> email
    email_drop: Path  # EMAIL_DROP_FILE of the run (ADR-0029)

    def read_emails(self, *, to: str | None = None) -> list[dict]:
        """Parsed JSON lines of the email drop file, oldest first (optionally only to ``to``)."""
        if not self.email_drop.is_file():
            return []
        emails = [json.loads(line) for line in self.email_drop.read_text(encoding="utf-8").splitlines() if line.strip()]
        if to is not None:
            emails = [e for e in emails if str(e.get("to", "")).lower() == to.lower()]
        return emails


# ---------------------------------------------------------------------------------------
# Pure helpers (tested without a browser or a server)
# ---------------------------------------------------------------------------------------
def find_free_port(host: str = "127.0.0.1") -> int:
    """A TCP port that is free on ``host`` right now (the OS picks it)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def compose_env(
    *,
    base_url: str,
    db_url: str,
    email_drop: Path,
    demo_mode: bool = True,
    frontend_dist: Path | None = None,
    env: Mapping[str, str] | None = None,
    inherited: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """The environment of the app under test (ADR-0036).

    Starts from ``inherited`` (default ``os.environ``) minus every app setting, then sets
    test mode with fakes, the fixed demo date, demo mode, no rate limits, the embedded job
    worker, the run's database and email drop file, and finally applies ``env`` overrides.
    """
    source = dict(os.environ if inherited is None else inherited)
    out = {k: v for k, v in source.items() if not k.upper().startswith(_INHERITED_PREFIXES)}
    out.update(
        {
            "APP_ENV": "test",
            "LAUNCH_FAKE_SERVICES": "1",
            "LAUNCH_TODAY": DEMO_TODAY.isoformat(),
            "DEMO_MODE": "1" if demo_mode else "0",
            "RATE_LIMITS_ENABLED": "0",
            "JOBS_EMBEDDED_WORKER": "1",
            "LAUNCH_DB_URL": db_url,
            "EMAIL_DROP_FILE": str(email_drop),
            "APP_BASE_URL": base_url,
            "LAUNCH_CORS_ORIGINS": base_url,
            "FRONTEND_DIST": str(frontend_dist or FRONTEND_DIR / "dist"),
            "PYTHONPATH": str(REPO_ROOT),
            "PYTHONUTF8": "1",
        }
    )
    out.update(dict(env or {}))
    return out


def screenshot_name(name: str, device: str, theme: str) -> str:
    """``<flow>-<desktop|phone>-<light|dark>.png`` (ADR-0036 evidence convention)."""
    if device not in DEVICES:
        raise ValueError(f"device must be one of {sorted(DEVICES)}, got {device!r}")
    if theme not in THEMES:
        raise ValueError(f"theme must be one of {THEMES}, got {theme!r}")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        raise ValueError(f"screenshot names are kebab-case, got {name!r}")
    return f"{name}-{device}-{theme}.png"


_RAW_JSON_PATTERNS = (
    re.compile(r'\{\s*"[A-Za-z_][\w-]*"\s*:'),  # a JSON object
    re.compile(r'\[\s*\{\s*"'),  # a JSON array of objects
    re.compile(r"Traceback \(most recent call last\)"),
    re.compile(r"\[object Object\]"),
    re.compile(r'"(?:error|detail|details|request_id)"\s*:'),
)


def find_raw_json(text: str) -> list[str]:
    """Snippets of ``text`` that look like raw JSON, stack traces or unrendered objects."""
    hits: list[str] = []
    for pattern in _RAW_JSON_PATTERNS:
        for match in pattern.finditer(text):
            start = max(0, match.start() - 20)
            hits.append(text[start : match.end() + 40].replace("\n", " "))
    return hits


def wait_for_ready(
    base_url: str,
    *,
    get: Callable[[str], int],
    timeout_s: float = READY_TIMEOUT_S,
    sleep: Callable[[float], None] = time.sleep,
    alive: Callable[[], bool] = lambda: True,
    clock: Callable[[], float] = time.monotonic,
) -> str:
    """Polls ``/api/ready`` until it answers 200 and returns the path that did.

    While readiness is not implemented (``/api/ready`` answers 404) it falls back to
    ``/api/health``. ``get(url)`` returns the HTTP status, raising ``OSError`` while the
    server is not accepting connections yet.
    """
    path = "/api/ready"
    deadline = clock() + timeout_s
    last = "no answer"
    while True:
        if not alive():
            raise RuntimeError(f"the app exited before it was ready (last: {last})")
        try:
            status = get(base_url + path)
            last = f"{path} -> {status}"
            if status == 200:
                return path
            if status == 404 and path == "/api/ready":
                path = "/api/health"
                continue
        except OSError as exc:
            last = f"{path} -> {type(exc).__name__}"
        if clock() >= deadline:
            raise TimeoutError(f"the app was not ready within {timeout_s:.0f} s (last: {last})")
        sleep(0.2)


_FRONTEND_INPUTS = (
    "src",
    "public",
    "index.html",
    "package.json",
    "package-lock.json",
    "vite.config.ts",
    "tailwind.config.ts",
    "postcss.config.js",
    "tsconfig.json",
    "tsconfig.app.json",
    "tsconfig.node.json",
)


def _newest_mtime(paths: list[Path]) -> float:
    newest = 0.0
    for p in paths:
        if p.is_file():
            newest = max(newest, p.stat().st_mtime)
        elif p.is_dir():
            for f in p.rglob("*"):
                if f.is_file():
                    newest = max(newest, f.stat().st_mtime)
    return newest


def frontend_is_stale(frontend_dir: Path = FRONTEND_DIR) -> bool:
    """True when ``dist/`` is missing, was not built by ``build_frontend`` (no stamp), or
    any source or config file is newer than the stamp."""
    stamp = frontend_dir / "dist" / BUILD_STAMP
    if not (frontend_dir / "dist" / "index.html").is_file() or not stamp.is_file():
        return True
    return _newest_mtime([frontend_dir / name for name in _FRONTEND_INPUTS]) > stamp.stat().st_mtime


# ---------------------------------------------------------------------------------------
# Build, start, log in
# ---------------------------------------------------------------------------------------
def _npm() -> str:
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if not npm:
        raise RuntimeError("npm is not on PATH; install Node.js 20+ to build the frontend")
    return npm


def build_frontend(*, force: bool = False) -> Path:
    """``npm run build`` (with the ``/design`` gallery) when ``frontend/dist`` is missing or
    stale; returns the dist path. Installs packages with ``npm ci`` first if needed."""
    dist = FRONTEND_DIR / "dist"
    if not force and not frontend_is_stale(FRONTEND_DIR):
        return dist
    npm = _npm()
    if not (FRONTEND_DIR / "node_modules").is_dir():
        subprocess.run([npm, "ci", "--no-audit", "--no-fund"], cwd=FRONTEND_DIR, check=True, timeout=900)
    env = {**os.environ, "VITE_DESIGN_GALLERY": "1"}
    result = subprocess.run(
        [npm, "run", "build"], cwd=FRONTEND_DIR, env=env, capture_output=True, text=True, timeout=900
    )
    if result.returncode != 0:
        raise RuntimeError(f"frontend build failed:\n{result.stdout[-4000:]}\n{result.stderr[-4000:]}")
    (dist / BUILD_STAMP).write_text("design-gallery=1\n", encoding="utf-8")
    return dist


def _migrate(db_url: str) -> None:
    """Migrate the run's database to head: ``init_db`` (T-005) or Alembic directly."""
    try:
        from ..persistence.engine import create_db_engine, init_db

        engine = create_db_engine(db_url)
        try:
            init_db(engine)
        finally:
            engine.dispose()
        return
    except NotImplementedError:
        pass
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(REPO_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(REPO_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", db_url)
    cfg.attributes["configure_logger"] = False
    command.upgrade(cfg, "head")


def _seed(env: Mapping[str, str], stage: str, plan: str) -> tuple[str | None, dict[str, str]]:
    from ..config import load_settings
    from ..demo import seed_case
    from ..domain.billing import PlanId

    result = seed_case(load_settings(dict(env)), stage, plan=PlanId(plan))
    return result.case_id, dict(result.users)


def _http_status(url: str) -> int:
    import httpx

    try:
        return httpx.get(url, timeout=2.0).status_code
    except httpx.TransportError as exc:  # not listening yet
        raise OSError(str(exc)) from exc


def _stop(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=10)


@contextmanager
def running_app(
    *,
    seed_stage: str | None = None,
    plan: str = "launch",
    demo_mode: bool = True,
    env: Mapping[str, str] | None = None,
) -> Iterator[RunningApp]:
    """Temp dir + SQLite migrated to head, fake services, seeding before start, uvicorn on a
    free port, waits for ``/api/ready`` (30 s; ``/api/health`` until readiness exists) (ADR-0036)."""
    tmp = Path(tempfile.mkdtemp(prefix="ui-run-"))
    db_url = f"sqlite:///{(tmp / 'app.db').as_posix()}"
    email_drop = tmp / "emails.jsonl"
    port = find_free_port()
    base_url = f"http://127.0.0.1:{port}"
    run_env = compose_env(base_url=base_url, db_url=db_url, email_drop=email_drop, demo_mode=demo_mode, env=env)
    log_path = tmp / "server.log"
    proc: subprocess.Popen | None = None
    try:
        _migrate(db_url)
        case_id: str | None = None
        users: dict[str, str] = {}
        if seed_stage is not None:
            case_id, users = _seed(run_env, seed_stage, plan)
        with open(log_path, "wb") as log:
            proc = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "launch_agents.api.app:create_app", "--factory",
                 "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
                cwd=REPO_ROOT, env=run_env, stdout=log, stderr=subprocess.STDOUT,
            )
        try:
            wait_for_ready(base_url, get=_http_status, alive=lambda: proc is not None and proc.poll() is None)
        except (RuntimeError, TimeoutError) as exc:
            tail = log_path.read_text(encoding="utf-8", errors="replace")[-3000:] if log_path.exists() else ""
            raise RuntimeError(f"{exc}\n--- server log ---\n{tail}") from exc
        yield RunningApp(base_url=base_url, db_url=db_url, case_id=case_id, users=users, email_drop=email_drop)
    finally:
        if proc is not None:
            _stop(proc)
        shutil.rmtree(tmp, ignore_errors=True)


def login(page: "Page", app: RunningApp, who: str = "alice") -> None:
    """Log in through the real login form (labels "Email" and "Password", button "Log in")."""
    email = app.users.get(who)
    if not email:
        raise KeyError(f"no seeded user {who!r}; seed at least the 'account' stage (users: {sorted(app.users)})")
    page.goto(f"{app.base_url}/login")
    page.get_by_label("Email").fill(email)
    page.get_by_label("Password").fill(DEMO_PASSWORD)
    page.get_by_role("button", name="Log in").click()
    page.wait_for_url(re.compile(r".*/app(?:[/?#].*)?$"), timeout=30_000)


# ---------------------------------------------------------------------------------------
# Screenshots and page assertions
# ---------------------------------------------------------------------------------------
def capture_matrix(
    browser: "Browser",
    url: str,
    name: str,
    out_dir: Path,
    *,
    prepare: Callable[["Page"], None] | None = None,
    storage_state: str | None = None,
) -> list[Path]:
    """Desktop/phone x light/dark screenshots ``<name>-<device>-<theme>.png`` (ADR-0036).

    Each capture uses a fresh context with the theme forced (``launch.theme`` and the
    color scheme), runs ``prepare(page)`` after loading, and keeps each PNG under 500 KB
    (a full-page capture that is too large falls back to the viewport)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for device, viewport in DEVICES.items():
        for theme in THEMES:
            context = browser.new_context(
                viewport=viewport,
                color_scheme=theme,  # type: ignore[arg-type]
                device_scale_factor=1,
                storage_state=storage_state,
                reduced_motion="reduce",
            )
            context.add_init_script(f"try{{localStorage.setItem('launch.theme','{theme}')}}catch(e){{}}")
            page = context.new_page()
            try:
                page.goto(url)
                page.wait_for_load_state("networkidle")
                if prepare is not None:
                    prepare(page)
                page.wait_for_timeout(150)
                path = out_dir / screenshot_name(name, device, theme)
                page.screenshot(path=str(path), full_page=True)
                if path.stat().st_size > MAX_SCREENSHOT_BYTES:
                    page.screenshot(path=str(path), full_page=False)
                paths.append(path)
            finally:
                context.close()
    return paths


_SCROLL_JS = """() => {
  const vw = document.documentElement.clientWidth;
  const sw = Math.max(document.documentElement.scrollWidth, document.body ? document.body.scrollWidth : 0);
  const inScroller = (el) => {
    for (let p = el.parentElement; p && p !== document.body; p = p.parentElement) {
      const o = getComputedStyle(p).overflowX;
      if (o === 'auto' || o === 'scroll' || o === 'hidden' || o === 'clip') return true;
    }
    return false;
  };
  const offenders = [];
  if (sw > vw + 1) {
    for (const el of document.querySelectorAll('body *')) {
      const r = el.getBoundingClientRect();
      if (r.right > vw + 1 && r.width > 0 && !inScroller(el)) {
        offenders.push(el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + (el.className && typeof el.className === 'string' ? '.' + el.className.split(' ').slice(0, 3).join('.') : ''));
        if (offenders.length >= 5) break;
      }
    }
  }
  return { viewport: vw, scrollWidth: sw, offenders };
}"""


def assert_no_horizontal_scroll(page: "Page") -> None:
    """The page itself never scrolls sideways (scrollable children such as a tab list may)."""
    info = page.evaluate(_SCROLL_JS)
    if info["scrollWidth"] > info["viewport"] + 1:
        raise AssertionError(
            f"page scrolls horizontally at {info['viewport']}px (scrollWidth {info['scrollWidth']}); "
            f"widest elements: {info['offenders']}"
        )


def assert_no_raw_json(page: "Page") -> None:
    """No raw JSON, stack trace or ``[object Object]`` in the visible text."""
    hits = find_raw_json(page.inner_text("body"))
    if hits:
        raise AssertionError(f"raw data shown to the user: {hits[:3]}")
