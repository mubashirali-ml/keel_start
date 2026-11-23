"""UI recorded-run helper (ADR-0036, T-011): free ports, env composition, screenshot naming,
readiness polling, the email drop and raw-JSON detection, all without a browser or a server."""

from __future__ import annotations

import json
import os
import socket
import time
from pathlib import Path

import pytest

from launch_agents.devtools import ui_run
from launch_agents.devtools.brand_assets import brand_text, og_image_html
from launch_agents.devtools.ui_run import (
    DEMO_PASSWORD,
    DEMO_TODAY,
    DEVICES,
    THEMES,
    RunningApp,
    compose_env,
    find_free_port,
    find_raw_json,
    frontend_is_stale,
    screenshot_name,
    wait_for_ready,
)


# ---------------------------------------------------------------------------------------
# constants
# ---------------------------------------------------------------------------------------
def test_demo_constants_match_adr_0036():
    assert DEMO_TODAY.isoformat() == "2026-11-23"
    assert DEMO_PASSWORD == "demo-password-2026"
    assert DEVICES["desktop"]["width"] == 1280
    assert DEVICES["phone"]["width"] == 390
    assert THEMES == ("light", "dark")


# ---------------------------------------------------------------------------------------
# free port
# ---------------------------------------------------------------------------------------
def test_find_free_port_returns_a_bindable_port():
    port = find_free_port()
    assert 1024 <= port <= 65535
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", port))  # still free: nothing kept it open


def test_find_free_port_gives_different_ports_while_one_is_taken():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as held:
        held.bind(("127.0.0.1", 0))
        held.listen(1)
        taken = held.getsockname()[1]
        assert all(find_free_port() != taken for _ in range(5))


# ---------------------------------------------------------------------------------------
# environment composition
# ---------------------------------------------------------------------------------------
def _env(**kw):
    defaults = dict(
        base_url="http://127.0.0.1:5555",
        db_url="sqlite:///C:/tmp/run/app.db",
        email_drop=Path("/tmp/run/emails.jsonl"),
        inherited={},
    )
    defaults.update(kw)
    return compose_env(**defaults)


def test_compose_env_sets_test_mode_fakes_and_the_run_resources():
    env = _env()
    assert env["APP_ENV"] == "test"
    assert env["LAUNCH_FAKE_SERVICES"] == "1"
    assert env["LAUNCH_TODAY"] == "2026-11-23"
    assert env["DEMO_MODE"] == "1"
    assert env["RATE_LIMITS_ENABLED"] == "0"
    assert env["JOBS_EMBEDDED_WORKER"] == "1"
    assert env["LAUNCH_DB_URL"] == "sqlite:///C:/tmp/run/app.db"
    assert env["EMAIL_DROP_FILE"] == str(Path("/tmp/run/emails.jsonl"))
    assert env["APP_BASE_URL"] == "http://127.0.0.1:5555"
    assert env["LAUNCH_CORS_ORIGINS"] == "http://127.0.0.1:5555"
    assert env["FRONTEND_DIST"].replace("\\", "/").endswith("frontend/dist")
    assert Path(env["PYTHONPATH"]) == ui_run.REPO_ROOT


def test_compose_env_demo_mode_off():
    assert _env(demo_mode=False)["DEMO_MODE"] == "0"


def test_compose_env_drops_inherited_app_settings_but_keeps_the_system():
    inherited = {
        "PATH": "/usr/bin",
        "SYSTEMROOT": "C:/Windows",
        "LLM_PROVIDER": "anthropic",
        "ANTHROPIC_API_KEY": "sk-real",
        "DATABASE_URL": "postgresql://prod",
        "STRIPE_SECRET_KEY": "sk_live",
        "DEMO_MODE": "0",
        "BRAND_NAME": "Other",
        "APP_ENV": "production",
    }
    env = _env(inherited=inherited)
    assert env["PATH"] == "/usr/bin"
    assert env["SYSTEMROOT"] == "C:/Windows"
    for key in ("LLM_PROVIDER", "ANTHROPIC_API_KEY", "DATABASE_URL", "STRIPE_SECRET_KEY", "BRAND_NAME"):
        assert key not in env
    assert env["APP_ENV"] == "test"
    assert env["DEMO_MODE"] == "1"


def test_compose_env_overrides_win():
    env = _env(env={"SUPPORT_EMAIL": "help@example.com", "RATE_LIMITS_ENABLED": "1"})
    assert env["SUPPORT_EMAIL"] == "help@example.com"
    assert env["RATE_LIMITS_ENABLED"] == "1"


def test_compose_env_is_valid_test_settings():
    from launch_agents.config import AppEnv, load_settings

    settings = load_settings(_env())
    assert settings.app_env == AppEnv.TEST
    assert settings.fake_services is True
    assert settings.demo_mode is True
    assert settings.rate_limits_enabled is False
    assert settings.today == DEMO_TODAY
    assert settings.email_drop_file and settings.email_drop_file.endswith("emails.jsonl")


def test_compose_env_reads_os_environ_by_default(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("SOME_TOOL_HOME", "/opt/tool")
    env = compose_env(base_url="http://x", db_url="sqlite://", email_drop=Path("e.jsonl"))
    assert "LLM_PROVIDER" not in env
    assert env["SOME_TOOL_HOME"] == "/opt/tool"
    assert os.environ["LLM_PROVIDER"] == "anthropic"  # the caller's environment is untouched


# ---------------------------------------------------------------------------------------
# screenshot naming
# ---------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("name", "device", "theme", "expected"),
    [
        ("design", "desktop", "light", "design-desktop-light.png"),
        ("app-redirect", "phone", "dark", "app-redirect-phone-dark.png"),
    ],
)
def test_screenshot_name(name, device, theme, expected):
    assert screenshot_name(name, device, theme) == expected


@pytest.mark.parametrize(
    ("name", "device", "theme"),
    [("design", "tablet", "light"), ("design", "desktop", "sepia"), ("Design Page", "desktop", "light"), ("", "phone", "dark")],
)
def test_screenshot_name_rejects_bad_parts(name, device, theme):
    with pytest.raises(ValueError):
        screenshot_name(name, device, theme)


def test_the_matrix_has_four_names_per_flow():
    names = {screenshot_name("login", d, t) for d in DEVICES for t in THEMES}
    assert names == {"login-desktop-light.png", "login-desktop-dark.png", "login-phone-light.png", "login-phone-dark.png"}


# ---------------------------------------------------------------------------------------
# readiness
# ---------------------------------------------------------------------------------------
class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


def test_wait_for_ready_polls_until_ready():
    answers = iter([OSError("refused"), OSError("refused"), 503, 200])
    seen: list[str] = []

    def get(url: str) -> int:
        seen.append(url)
        answer = next(answers)
        if isinstance(answer, Exception):
            raise answer
        return answer

    clock = FakeClock()
    assert wait_for_ready("http://h", get=get, sleep=clock.sleep, clock=clock) == "/api/ready"
    assert seen == ["http://h/api/ready"] * 4


def test_wait_for_ready_falls_back_to_health_while_ready_is_missing():
    seen: list[str] = []

    def get(url: str) -> int:
        seen.append(url)
        return 404 if url.endswith("/api/ready") else 200

    clock = FakeClock()
    assert wait_for_ready("http://h", get=get, sleep=clock.sleep, clock=clock) == "/api/health"
    assert seen == ["http://h/api/ready", "http://h/api/health"]


def test_wait_for_ready_times_out_after_30_seconds():
    clock = FakeClock()
    with pytest.raises(TimeoutError, match="30 s"):
        wait_for_ready("http://h", get=lambda url: 503, sleep=clock.sleep, clock=clock)
    assert 30 <= clock.now < 31


def test_wait_for_ready_stops_when_the_server_dies():
    with pytest.raises(RuntimeError, match="exited"):
        wait_for_ready("http://h", get=lambda url: 503, alive=lambda: False, sleep=lambda s: None)


# ---------------------------------------------------------------------------------------
# email drop
# ---------------------------------------------------------------------------------------
def test_read_emails_parses_the_drop_file_oldest_first(tmp_path):
    drop = tmp_path / "emails.jsonl"
    rows = [
        {"to": "alice@example.com", "subject": "Keelstart: Confirm your email", "template": "verify_email"},
        {"to": "Bob@Example.com", "subject": "Keelstart: Alice invited you", "template": "invite_cofounder"},
        {"to": "alice@example.com", "subject": "Keelstart: Please sign", "template": "signature_needed"},
    ]
    drop.write_text("\n".join(json.dumps(r) for r in rows) + "\n\n", encoding="utf-8")
    app = RunningApp(base_url="http://x", db_url="sqlite://", case_id=None, users={}, email_drop=drop)
    assert [e["template"] for e in app.read_emails()] == ["verify_email", "invite_cofounder", "signature_needed"]
    assert [e["template"] for e in app.read_emails(to="ALICE@example.com")] == ["verify_email", "signature_needed"]
    assert len(app.read_emails(to="bob@example.com")) == 1


def test_read_emails_without_a_drop_file(tmp_path):
    app = RunningApp(base_url="http://x", db_url="sqlite://", case_id=None, users={}, email_drop=tmp_path / "none.jsonl")
    assert app.read_emails() == []


# ---------------------------------------------------------------------------------------
# raw JSON detection
# ---------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "text",
    [
        'Error: {"error": {"code": "not_found"}}',
        '[{"id": 1}]',
        "Traceback (most recent call last):\n  File x",
        "Name: [object Object]",
        'oops "request_id": "req-1"',
    ],
)
def test_find_raw_json_flags_raw_data(text):
    assert find_raw_json(text)


@pytest.mark.parametrize(
    "text",
    [
        "We couldn't find this company. Back to your companies",
        "Reference: req-7f3a9c21",
        "Use {curly} words and [brackets] in normal copy: fine.",
        "60% equity, 48 months, 12-month cliff",
    ],
)
def test_find_raw_json_accepts_friendly_copy(text):
    assert find_raw_json(text) == []


# ---------------------------------------------------------------------------------------
# frontend staleness
# ---------------------------------------------------------------------------------------
def _frontend(tmp_path: Path) -> Path:
    fe = tmp_path / "frontend"
    (fe / "src").mkdir(parents=True)
    (fe / "src" / "main.tsx").write_text("x", encoding="utf-8")
    (fe / "package-lock.json").write_text("{}", encoding="utf-8")
    return fe


def test_frontend_is_stale_without_a_build(tmp_path):
    assert frontend_is_stale(_frontend(tmp_path)) is True


def test_frontend_is_stale_without_the_stamp(tmp_path):
    fe = _frontend(tmp_path)
    (fe / "dist").mkdir()
    (fe / "dist" / "index.html").write_text("<html></html>", encoding="utf-8")
    assert frontend_is_stale(fe) is True  # e.g. a plain `npm run build` without the gallery


def test_frontend_is_fresh_after_a_stamped_build_and_stale_after_an_edit(tmp_path):
    fe = _frontend(tmp_path)
    (fe / "dist").mkdir()
    (fe / "dist" / "index.html").write_text("<html></html>", encoding="utf-8")
    stamp = fe / "dist" / ui_run.BUILD_STAMP
    stamp.write_text("design-gallery=1\n", encoding="utf-8")
    later = time.time() + 5
    os.utime(stamp, (later, later))
    assert frontend_is_stale(fe) is False
    newer = later + 5
    os.utime(fe / "src" / "main.tsx", (newer, newer))
    assert frontend_is_stale(fe) is True


# ---------------------------------------------------------------------------------------
# login needs seeded users; brand assets come from the brand constants
# ---------------------------------------------------------------------------------------
def test_login_needs_a_seeded_user(tmp_path):
    app = RunningApp(base_url="http://x", db_url="sqlite://", case_id=None, users={}, email_drop=tmp_path / "e.jsonl")
    with pytest.raises(KeyError, match="seed"):
        ui_run.login(page=None, app=app)  # type: ignore[arg-type]


def test_brand_assets_read_the_one_brand_source():
    text = brand_text()
    assert text.tagline == "Launch your company with a team of AI agents"
    html = og_image_html(text)
    assert text.name in html and text.tagline in html
    assert "<script" not in html
