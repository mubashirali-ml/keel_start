"""T-011 feature run: the frontend foundation in a real browser (ADR-0005, ADR-0036).

Builds the frontend, starts the app with ``running_app()`` (fakes, no seed), and with
Playwright: checks every ``/design`` component section, the theme toggle surviving a reload,
a visible focus ring while tabbing through the header, the landing page's logo, brand name,
title and disclaimer, the logged-out redirect from ``/app/cases/unknown/overview`` to
``/login?next=...``, no inline scripts, no horizontal scroll at 390 px and no raw JSON, the
marketing first-load JS budget, then saves the screenshot matrices to ``evidence/T-011/``.

    bash scripts/record_run.sh T-011
"""

from __future__ import annotations

import gzip
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import Page, sync_playwright

from launch_agents.devtools.ui_run import (
    assert_no_horizontal_scroll,
    assert_no_raw_json,
    build_frontend,
    capture_matrix,
    running_app,
)

EVIDENCE = Path(__file__).resolve().parent
BRAND = "Keelstart"
TAGLINE = "Launch your company with a team of AI agents"
DISCLAIMER = f"Not legal advice. {BRAND} is not a law firm."
GALLERY_SECTIONS = [
    "Logo", "Colors", "Typography", "Button", "IconButton", "Input", "Textarea", "Select", "Checkbox", "Switch",
    "RadioGroup", "FormField", "SegmentedControl", "Card", "Tabs", "Badge", "StatusBadge", "Dialog", "ConfirmDialog",
    "Toast", "Popover", "Menu", "Tooltip", "Banner", "TrustNote", "PlanGate", "EmptyState", "ErrorState", "Skeleton",
    "Progress", "Avatar", "AgentAvatar", "Table", "Markdown", "Countdown",
]
FIRST_LOAD_BUDGET_GZIP = 250 * 1024  # ADR-0035: marketing and auth pages

checks: list[str] = []


def ok(message: str) -> None:
    checks.append(message)
    print(f"  ok  {message}")


def inline_scripts(page: Page) -> int:
    return page.evaluate("() => document.querySelectorAll('script:not([src])').length")


def focus_info(page: Page) -> dict:
    return page.evaluate(
        """() => {
          const el = document.activeElement;
          const s = getComputedStyle(el);
          return {
            tag: el.tagName.toLowerCase(),
            name: el.getAttribute('aria-label') || el.textContent.trim().slice(0, 40),
            inHeader: !!el.closest('header') || el.getAttribute('href') === '#main-content',
            boxShadow: s.boxShadow,
            outline: s.outlineStyle + ' ' + s.outlineWidth,
          };
        }"""
    )


# Demo data for the stubbed shell (ADR-0036 scenario: Alice Chen and Bob Diaz).
CASE_ID = "case_0123456789ab"
ME = {
    "user": {"id": "usr_alice0000001", "email": "alice@example.com", "full_name": "Alice Chen",
             "email_verified_at": None, "is_admin": False, "created_at": "2026-11-20T09:00:00Z"},
    "plan": "launch",
    "subscription": {"user_id": "usr_alice0000001", "plan": "launch", "interval": "month", "status": "active",
                     "current_period_end": None, "cancel_at_period_end": False,
                     "provider_customer_id": None, "provider_subscription_id": None},
    "email_verified": False,
    "companies": [{"id": CASE_ID, "company_name": "Acme Bakery Software", "created_at": "2026-11-20T09:00:00Z",
                   "updated_at": "2026-11-22T09:00:00Z", "percent": 33}],
    "csrf_token": "stub-csrf",
}
STEPS = [("facts", "Facts", "done"), ("name", "Name", "done"), ("legal", "Legal", "in_progress"),
         ("cap_table", "Cap table", "not_started"), ("website", "Website", "not_started"),
         ("registration", "Registration", "attention")]
CASE = {
    "id": CASE_ID, "created_at": "2026-11-20T09:00:00Z", "updated_at": "2026-11-22T09:00:00Z",
    "facts": {"business_description": "bookkeeping software for small bakeries",
              "founders": [{"id": "f1", "name": "Alice Chen", "email": "alice@example.com", "equity_percent": "60",
                            "vesting_months": 48, "cliff_months": 12},
                           {"id": "f2", "name": "Bob Diaz", "email": "bob@example.com", "equity_percent": "40",
                            "vesting_months": None, "cliff_months": None}],
              "entity_type": "LLC", "state": "WY", "incorporation_date": "2026-12-01", "name_preferences": [],
              "company_name": "Acme Bakery Software",
              "website": {"pages": [], "services": [], "about": None, "contact_email": None, "contact_phone": None,
                          "contact_address": None, "extra_content": [], "style_notes": None}},
    "facts_locked": True, "active_agent": "law", "company_name": "Acme Bakery Software", "chosen_domain": None,
    "validation_issues": [], "missing_facts": [], "deadline_83b": "2026-12-31", "days_until_83b": 38,
    "progress": {"percent": 33, "steps": [{"id": i, "label": l, "status": s, "detail": ""} for i, l, s in STEPS]},
    "legal_issues": [], "my_role": "owner", "my_founder_id": "f1", "plan": "launch", "active_jobs": [],
}


def stub_api(context, *, demo_mode: bool) -> list[tuple[str, str | None]]:
    """Answers the wave-3 routes the shell needs; records (path, X-Act-As-Founder)."""
    import json

    seen: list[tuple[str, str | None]] = []

    def handle(route):
        req = route.request
        path = urlparse(req.url).path
        seen.append((path, req.headers.get("x-act-as-founder")))
        bodies = {
            "/api/auth/me": ME,
            "/api/config": {"brand_name": BRAND, "demo_mode": demo_mode, "payments_test_mode": True,
                            "hosting_configured": False, "support_email": "help@example.com", "yearly_enabled": True},
            "/api/cases": ME["companies"],
            f"/api/cases/{CASE_ID}": CASE,
        }
        if path in bodies:
            route.fulfill(status=200, content_type="application/json", body=json.dumps(bodies[path]))
        else:
            route.fulfill(status=404, content_type="application/json",
                          body=json.dumps({"error": {"code": "not_found", "message": "We couldn't find that.", "details": {}}}))

    context.route("**/api/**", handle)
    return seen


def app_shell_checks(browser, base: str) -> list[Path]:
    from launch_agents.devtools.ui_run import DEVICES, screenshot_name

    url = f"{base}/app/cases/{CASE_ID}/overview"
    # Desktop, demo mode: header, founder switcher, tabs, progress strip, banners.
    ctx = browser.new_context(viewport=DEVICES["desktop"])
    seen = stub_api(ctx, demo_mode=True)
    page = ctx.new_page()
    page.goto(url)
    tabs = page.get_by_role("tablist", name="Workspace views")
    tabs.wait_for()
    names = tabs.get_by_role("tab").all_inner_texts()
    print(f"tabs: {names}")
    assert names == ["Overview", "Names", "Legal", "Cap table", "Website", "Guide", "Team", "Audit"]
    assert page.get_by_role("list", name="Progress").get_by_role("listitem").count() == 6
    assert page.get_by_role("region", name="Chat").is_visible()
    assert page.get_by_text("Demo mode").first.is_visible()
    assert page.get_by_text("Confirm your email to sign documents.").is_visible()
    assert page.get_by_text("payments are simulated").is_visible()
    tabs.get_by_role("tab", name="Overview").focus()
    page.keyboard.press("ArrowRight")
    page.wait_for_url(re.compile(r".*/names$"))
    ok("shell: 8 workspace tabs (arrow keys move between them), 6-step strip, chat panel, banners, demo badge")
    page.get_by_role("combobox", name="Acting as").click()
    page.get_by_role("option", name="Bob Diaz").click()
    page.wait_for_timeout(300)
    acting = [h for p, h in seen if p.startswith(f"/api/cases/{CASE_ID}") and h]
    print(f"X-Act-As-Founder sent on company calls: {sorted(set(acting))}")
    assert "f2" in acting
    ok("demo mode: the founder switcher sends X-Act-As-Founder")
    page.get_by_role("button", name="Account: Alice Chen").click()
    assert page.get_by_role("menu").get_by_text("Launch plan").is_visible()
    assert page.get_by_role("menuitem", name="Log out").is_visible()
    page.keyboard.press("Escape")
    ok("account menu shows the plan badge and Log out")
    ctx.close()

    # Outside demo mode the switcher is absent and no act-as header is sent.
    ctx = browser.new_context(viewport=DEVICES["desktop"])
    seen = stub_api(ctx, demo_mode=False)
    page = ctx.new_page()
    page.goto(url)
    page.get_by_role("tablist", name="Workspace views").wait_for()
    assert page.get_by_text("Demo mode").count() == 0
    assert all(h is None for _, h in seen)
    ok("outside demo mode: no founder switcher, no X-Act-As-Founder")
    ctx.close()

    # Unknown company (logged in): friendly not-found page with a way back.
    ctx = browser.new_context(viewport=DEVICES["phone"])
    stub_api(ctx, demo_mode=False)
    page = ctx.new_page()
    page.goto(f"{base}/app/cases/case_unknown00000/overview")
    page.get_by_text("We couldn't find this company").wait_for()
    assert page.get_by_role("link", name="Back to your companies").is_visible()
    assert_no_raw_json(page)
    assert_no_horizontal_scroll(page)
    ok("unknown company: 'We couldn't find this company' with a way back, no raw JSON")
    ctx.close()

    # Screenshots of the shell (desktop and phone, light and dark) plus the phone workspace pane.
    shots: list[Path] = []
    for device, viewport in DEVICES.items():
        for theme in ("light", "dark"):
            ctx = browser.new_context(viewport=viewport, color_scheme=theme, reduced_motion="reduce")
            ctx.add_init_script(f"try{{localStorage.setItem('launch.theme','{theme}')}}catch(e){{}}")
            stub_api(ctx, demo_mode=True)
            page = ctx.new_page()
            page.goto(url)
            if device == "phone":
                page.get_by_role("radiogroup", name="Show").wait_for()
                assert_no_horizontal_scroll(page)
                page.get_by_role("radio", name="Workspace").click()
            page.get_by_role("tablist", name="Workspace views").wait_for()
            page.wait_for_load_state("networkidle")
            assert_no_horizontal_scroll(page)
            assert_no_raw_json(page)
            path = EVIDENCE / screenshot_name("app-shell-stubbed", device, theme)
            page.screenshot(path=str(path))
            shots.append(path)
            ctx.close()
    ok("shell at 390 px: Chat/Workspace switch, no sideways scroll")
    return shots


def main() -> int:
    print("== build ==")
    dist = build_frontend()
    print(f"frontend dist: {dist.relative_to(EVIDENCE.parents[1])}")

    with running_app() as app, sync_playwright() as p:
        base = app.base_url
        print(f"app: {base} (fake services, demo mode, no seed)")
        browser = p.chromium.launch()
        try:
            # ---------------------------------------------------------------- /design
            print("\n== /design: every component section ==")
            ctx = browser.new_context(viewport={"width": 1280, "height": 900}, color_scheme="light")
            page = ctx.new_page()
            page.goto(f"{base}/design")
            page.get_by_role("heading", level=1, name="Design system").wait_for()
            found = page.eval_on_selector_all("[data-gallery-section]", "els => els.map(e => e.dataset.gallerySection)")
            print(f"sections found ({len(found)}): {', '.join(found)}")
            assert found == GALLERY_SECTIONS, f"gallery sections differ: {found}"
            for name in GALLERY_SECTIONS:
                heading = page.get_by_role("heading", level=2, name=name, exact=True)
                assert heading.count() == 1, f"missing section heading {name}"
            ok(f"/design shows all {len(GALLERY_SECTIONS)} component sections")
            for variant in ("light", "dark", "one-colour"):
                assert page.locator(f'[data-logo-variant="{variant}"] [data-logo-mark]').count() >= 3
            sizes = page.eval_on_selector_all('[data-logo-variant="light"] svg[data-logo-mark]', "els => els.map(e => e.getAttribute('width'))")
            assert "16" in sizes and "32" in sizes, sizes
            ok(f"logo mark shown at {', '.join(sizes)} px in light, dark and one-colour variants")
            # Dialog opens, traps focus and closes on Escape.
            page.get_by_role("button", name="Open dialog").click()
            dialog = page.get_by_role("dialog", name="Invite a co-founder")
            dialog.wait_for()
            for _ in range(5):
                page.keyboard.press("Tab")
                assert page.evaluate("() => !!document.activeElement.closest('[role=dialog]')"), "focus escaped the dialog"
            page.keyboard.press("Escape")
            dialog.wait_for(state="detached")
            ok("Dialog traps focus and closes on Escape")
            page.get_by_role("button", name="Success toast").click()
            page.locator('[aria-live="polite"]', has_text="Document signed").first.wait_for(state="attached")
            ok("Toast is announced politely")
            assert inline_scripts(page) == 0
            assert_no_raw_json(page)
            ctx.close()

            # ---------------------------------------------------------------- theme toggle
            print("\n== theme toggle persists across reloads ==")
            ctx = browser.new_context(viewport={"width": 1280, "height": 800}, color_scheme="light")
            page = ctx.new_page()
            page.goto(f"{base}/")
            page.get_by_role("heading", level=1, name=TAGLINE).wait_for()
            assert "dark" not in (page.get_attribute("html", "class") or "")
            page.get_by_role("button", name="Theme: System. Change theme").click()
            page.get_by_role("menuitemradio", name="Dark").click()
            page.wait_for_function("() => document.documentElement.classList.contains('dark')")
            stored = page.evaluate("() => localStorage.getItem('launch.theme')")
            print(f"after choosing Dark: html.class={page.get_attribute('html', 'class')!r}, launch.theme={stored!r}")
            page.reload()
            # theme-init.js runs before first paint: the class is there at DOMContentLoaded.
            assert "dark" in (page.get_attribute("html", "class") or ""), "dark theme lost on reload"
            ok("dark theme chosen in the toggle is still applied after a reload (launch.theme=dark)")
            ctx.close()

            # ---------------------------------------------------------------- landing + focus ring
            print("\n== / (marketing layout): logo, brand, title, disclaimer, focus ring ==")
            ctx = browser.new_context(viewport={"width": 1280, "height": 800}, color_scheme="light")
            page = ctx.new_page()
            page.goto(f"{base}/")
            page.get_by_role("heading", level=1, name=TAGLINE).wait_for()
            title = page.title()
            print(f"title: {title!r}")
            assert title == f"{BRAND} · {TAGLINE}", title
            header_logo = page.locator("header [data-logo]")
            assert header_logo.count() == 1 and header_logo.is_visible()
            assert page.locator("header [data-logo-mark]").is_visible()
            assert page.locator("footer [data-logo]").is_visible()
            assert page.get_by_role("img", name=BRAND).first.is_visible()
            assert page.locator("header").get_by_text(BRAND, exact=True).is_visible()
            disclaimer = page.locator("footer [data-disclaimer]")
            print(f"footer disclaimer: {disclaimer.inner_text()!r}")
            assert disclaimer.inner_text() == DISCLAIMER
            ok("landing page shows the logo in header and footer, the brand name, the title and the disclaimer")
            focused = []
            for _ in range(6):
                page.keyboard.press("Tab")
                info = focus_info(page)
                if not info["inHeader"]:
                    break
                ring = info["boxShadow"] != "none" or not info["outline"].startswith("none")
                focused.append(f"{info['tag']} '{info['name']}' ring={'yes' if ring else 'NO'}")
                assert ring, f"no visible focus ring on {info}"
            print("tab order:", " -> ".join(focused))
            assert len(focused) >= 4, focused
            assert focused[0].startswith("a 'Skip to content'"), focused
            ok(f"tabbing through the header shows a focus ring on all {len(focused)} stops, skip link first")
            assert inline_scripts(page) == 0
            ctx.close()

            # ---------------------------------------------------------------- logged-out redirect
            print("\n== /app/cases/unknown/overview while logged out ==")
            ctx = browser.new_context(viewport={"width": 1280, "height": 800})
            page = ctx.new_page()
            page.goto(f"{base}/app/cases/unknown/overview")
            page.wait_for_url(re.compile(r".*/login\?next=.*"))
            target = urlparse(page.url)
            print(f"redirected to: {target.path}?{target.query}")
            assert target.path == "/login" and target.query == "next=%2Fapp%2Fcases%2Funknown%2Foverview"
            page.get_by_role("heading", level=1, name="Log in").wait_for()
            assert page.get_by_label("Email").is_visible() and page.get_by_label("Password").is_visible()
            assert page.title() == f"Log in · {BRAND}"
            ok("/app/* without a session redirects to /login?next=... and shows the login form")
            page.goto(f"{base}/no-such-page")
            page.get_by_text("We couldn't find that page").wait_for()
            ok("unknown paths show the friendly 404 page")
            ctx.close()

            # ---------------------------------------------------------------- 390px, raw JSON, inline scripts
            print("\n== 390 px: no horizontal scroll, no raw JSON, no inline scripts ==")
            ctx = browser.new_context(viewport={"width": 390, "height": 844})
            page = ctx.new_page()
            for path in ["/", "/pricing", "/login", "/signup", "/app/cases/unknown/overview", "/no-such-page", "/design"]:
                page.goto(f"{base}{path}")
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(100)
                assert_no_horizontal_scroll(page)
                assert_no_raw_json(page)
                assert inline_scripts(page) == 0
                print(f"  {path:<32} -> {urlparse(page.url).path}: no sideways scroll, no raw JSON, 0 inline scripts")
            ok("390 px pages never scroll sideways and show no raw JSON")
            ctx.close()

            # ---------------------------------------------------------------- first-load budget
            print("\n== marketing first-load JS (gzip) ==")
            ctx = browser.new_context(viewport={"width": 1280, "height": 800})
            page = ctx.new_page()
            scripts: list[str] = []
            page.on("response", lambda r: scripts.append(urlparse(r.url).path) if r.url.endswith(".js") else None)
            page.goto(f"{base}/")
            page.wait_for_load_state("networkidle")
            total = 0
            for path in sorted(set(scripts)):
                f = dist / path.lstrip("/")
                size = len(gzip.compress(f.read_bytes())) if f.is_file() else 0
                total += size
                print(f"  {path:<40} {size / 1024:6.1f} KB gzip")
            print(f"  total {total / 1024:.1f} KB (budget {FIRST_LOAD_BUDGET_GZIP // 1024} KB)")
            assert total < FIRST_LOAD_BUDGET_GZIP
            assert not any("DesignGallery" in s or "/onboarding" in s or "/settings" in s for s in scripts), scripts
            ok("landing loads only its own chunk; first-load JS is within the 250 KB budget")
            ctx.close()

            # ---------------------------------------------------------------- app shell (stubbed API)
            print("\n== app shell with a stubbed API (the auth and case routes arrive in wave 3) ==")
            shots_shell = app_shell_checks(browser, base)

            # ---------------------------------------------------------------- screenshots
            print("\n== screenshot matrices (1280/390 x light/dark) ==")
            shots = []
            shots += capture_matrix(browser, f"{base}/design", "design", EVIDENCE,
                                    prepare=lambda pg: pg.get_by_role("heading", level=1, name="Design system").wait_for())
            shots += capture_matrix(browser, f"{base}/design#gallery-Button", "design-controls", EVIDENCE,
                                    prepare=lambda pg: pg.locator("#gallery-Button").scroll_into_view_if_needed())
            shots += capture_matrix(browser, f"{base}/design#gallery-Banner", "design-feedback", EVIDENCE,
                                    prepare=lambda pg: pg.locator("#gallery-Banner").scroll_into_view_if_needed())
            shots += capture_matrix(browser, f"{base}/", "landing", EVIDENCE,
                                    prepare=lambda pg: pg.get_by_role("heading", level=1, name=TAGLINE).wait_for())
            shots += capture_matrix(browser, f"{base}/login", "login", EVIDENCE,
                                    prepare=lambda pg: pg.get_by_role("heading", level=1, name="Log in").wait_for())
            shots += capture_matrix(browser, f"{base}/app/cases/unknown/overview", "app-redirect", EVIDENCE,
                                    prepare=lambda pg: pg.wait_for_url(re.compile(r".*/login\?next=.*")))
            for s in shots + shots_shell:
                size = s.stat().st_size
                assert size < 500_000, f"{s.name} is {size} bytes"
                print(f"  {s.name:<40} {size / 1024:6.1f} KB")
            ok(f"{len(shots) + len(shots_shell)} screenshots saved to evidence/T-011/")
        finally:
            browser.close()

    print(f"\nALL CHECKS PASSED ({len(checks)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
