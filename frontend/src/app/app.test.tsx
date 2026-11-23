import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { makeCase, makeConfig, makeMe } from "@/test/fixtures";
import { setViewport } from "@/test/media";
import { apiError, headerOf, json, mockApi, notFound, unauthorized } from "@/test/mockFetch";
import { renderApp } from "@/test/renderWithProviders";

const CASE = makeCase();
const loggedIn = (overrides: Record<string, unknown> = {}) => ({
  "GET /api/auth/me": makeMe(),
  "GET /api/cases": [],
  [`GET /api/cases/${CASE.id}`]: CASE,
  ...overrides,
});

const location = () => screen.getByTestId("location").textContent;
const layout = async (name: string) => {
  await waitFor(() => expect(document.querySelector(`[data-layout="${name}"]`)).not.toBeNull());
};

describe("routes and layouts (ADR-0035)", () => {
  it.each([
    ["/", "landing"],
    ["/pricing", "Pricing"],
    ["/terms", "Terms of service"],
    ["/privacy", "Privacy"],
    ["/disclaimer", "Disclaimer"],
    ["/security", "Security"],
  ])("%s renders its placeholder in the marketing layout", async (path, heading) => {
    mockApi({});
    renderApp(path);
    await layout("marketing");
    if (heading === "landing") {
      expect(await screen.findByRole("heading", { level: 1, name: "Launch your company with a team of AI agents" })).toBeInTheDocument();
    } else {
      expect(await screen.findByRole("heading", { level: 1, name: heading })).toBeInTheDocument();
    }
    expect(screen.getByRole("navigation", { name: "Footer" })).toBeInTheDocument();
    expect(document.querySelector("[data-disclaimer]")).toHaveTextContent("Not legal advice.");
  });

  it.each([
    ["/login", "login"],
    ["/signup", "signup"],
    ["/forgot-password", "forgot-password"],
    ["/reset-password", "reset-password"],
    ["/verify-email", "verify-email"],
    ["/invite/tok_123", "invite"],
  ])("%s renders its placeholder in the auth layout", async (path, page) => {
    mockApi({});
    renderApp(path);
    await layout("auth");
    await waitFor(() => expect(document.querySelector(`[data-page="${page}"]`)).not.toBeNull());
  });

  it("sends logged-in users from the login page to the app (or ?next=)", async () => {
    mockApi(loggedIn());
    renderApp("/login?next=%2Fapp%2Fsettings");
    await waitFor(() => expect(location()).toBe("/app/settings"));
  });

  it("ignores an external ?next=", async () => {
    mockApi(loggedIn());
    renderApp("/login?next=%2F%2Fevil.example.com");
    await waitFor(() => expect(location()).toBe("/app"));
  });

  it.each([
    ["/app", "Your companies"],
    ["/app/onboarding", "Start a company"],
    ["/app/settings", "Settings"],
    ["/app/settings/security", "Settings"],
  ])("%s renders in the app layout for a logged-in user", async (path, heading) => {
    mockApi(loggedIn());
    renderApp(path);
    expect(await screen.findByRole("heading", { level: 1, name: heading })).toBeInTheDocument();
    await layout("app");
  });

  it("shows the test checkout page only when payments are fake", async () => {
    mockApi(loggedIn({ "GET /api/config": makeConfig({ payments_test_mode: true }) }));
    renderApp("/app/billing/test-checkout");
    expect(await screen.findByRole("heading", { level: 1, name: "Test checkout" })).toBeInTheDocument();
  });

  it("hides the test checkout page when payments are real", async () => {
    mockApi(loggedIn());
    renderApp("/app/billing/test-checkout");
    expect(await screen.findByText("We couldn't find that page")).toBeInTheDocument();
  });

  it("renders the admin area for admins", async () => {
    mockApi(loggedIn({ "GET /api/auth/me": makeMe({}, { is_admin: true }) }));
    renderApp("/admin/usage");
    expect(await screen.findByRole("heading", { level: 1, name: "Admin" })).toBeInTheDocument();
    await layout("app");
  });

  it("shows a friendly 'not available' page to non-admins", async () => {
    mockApi(loggedIn());
    renderApp("/admin");
    expect(await screen.findByText("This page isn't available")).toBeInTheDocument();
    await layout("app");
  });

  it.each(["/nope", "/app/nope", "/app/settings/nope", "/app/cases/case_0123456789ab/nope"])("%s shows the 404 page", async (path) => {
    mockApi(loggedIn());
    renderApp(path);
    expect(await screen.findByText("We couldn't find that page")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Go to the home page" })).toHaveAttribute("href", "/");
  });

  it("serves the /design gallery in a bare layout", async () => {
    mockApi({});
    renderApp("/design");
    expect(await screen.findByRole("heading", { level: 1, name: "Design system" }, { timeout: 5000 })).toBeInTheDocument();
    await layout("bare");
  });
});

describe("authentication boundaries", () => {
  it.each(["/app", "/app/cases/unknown/overview", "/app/settings/billing", "/admin"])(
    "%s without a session redirects to /login?next=...",
    async (path) => {
      mockApi({ "GET /api/auth/me": unauthorized() });
      renderApp(path);
      await waitFor(() => expect(location()).toBe(`/login?next=${encodeURIComponent(path)}`));
      await layout("auth");
    },
  );

  it("also redirects while the auth routes do not exist yet (404 from /api/auth/me)", async () => {
    mockApi({});
    renderApp("/app/cases/unknown/overview");
    await waitFor(() => expect(location()).toBe("/login?next=%2Fapp%2Fcases%2Funknown%2Foverview"));
  });

  it("a 401 from any call redirects to the login page", async () => {
    mockApi(loggedIn({ [`GET /api/cases/${CASE.id}`]: unauthorized() }));
    renderApp(`/app/cases/${CASE.id}/legal`);
    await waitFor(() => expect(location()).toBe(`/login?next=${encodeURIComponent(`/app/cases/${CASE.id}/legal`)}`));
  });
});

describe("workspace (ADR-0019, ADR-0035)", () => {
  it("shows 'We couldn't find this company' with a way back, never raw JSON", async () => {
    mockApi(loggedIn({ "GET /api/cases/unknown": notFound() }));
    renderApp("/app/cases/unknown/overview");
    expect(await screen.findByText("We couldn't find this company")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to your companies" })).toHaveAttribute("href", "/app");
    expect(document.body.textContent).not.toMatch(/"error"|\{"/);
  });

  it("shows a friendly error with a retry when the company can't be loaded", async () => {
    const user = userEvent.setup();
    let calls = 0;
    mockApi(
      loggedIn({
        [`GET /api/cases/${CASE.id}`]: () => {
          calls += 1;
          return calls === 1 ? apiError(503, "temporarily_unavailable", "We're temporarily unavailable.") : json(CASE);
        },
      }),
    );
    renderApp(`/app/cases/${CASE.id}/overview`);
    expect(await screen.findByText("We couldn't open this company")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByRole("tablist", { name: "Workspace views" })).toBeInTheDocument();
  });

  it("renders the shell: skip link, header, chat slot, 8 tabs and the 6-step strip", async () => {
    mockApi(loggedIn());
    renderApp(`/app/cases/${CASE.id}`);
    const tabs = await screen.findByRole("tablist", { name: "Workspace views" });
    expect(within(tabs).getAllByRole("tab").map((t) => t.textContent)).toEqual([
      "Overview",
      "Names",
      "Legal",
      "Cap table",
      "Website",
      "Guide",
      "Team",
      "Audit",
    ]);
    expect(within(tabs).getByRole("tab", { name: "Overview" })).toHaveAttribute("aria-selected", "true");
    expect(within(screen.getByRole("list", { name: "Progress" })).getAllByRole("listitem")).toHaveLength(6);
    expect(screen.getByRole("region", { name: "Chat" })).toBeInTheDocument();
    expect(await screen.findByText("No messages yet")).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Overview" })).toBeInTheDocument();

    const header = screen.getByRole("banner");
    expect(within(header).getByRole("link", { name: "Keelstart home" })).toHaveAttribute("href", "/app");
    expect(within(header).getByRole("button", { name: /Switch company. Current: Acme Bakery Software/ })).toBeInTheDocument();
    expect(within(header).getByRole("button", { name: /Theme:/ })).toBeInTheDocument();
    expect(within(header).getByRole("button", { name: "Help" })).toBeInTheDocument();
    expect(within(header).getByRole("progressbar", { name: "Progress" })).toHaveAttribute("aria-valuetext", "33%");
    expect(within(header).getByRole("button", { name: "Account: Alice Chen" })).toBeInTheDocument();

    // Skip link is the first focusable element and targets the main content.
    const user = userEvent.setup();
    await user.tab();
    expect(document.activeElement).toHaveTextContent("Skip to content");
    expect(document.activeElement).toHaveAttribute("href", "#main-content");
    expect(document.getElementById("main-content")).not.toBeNull();
    // Logical order: logo, company switcher, then the header controls.
    await user.tab();
    expect(document.activeElement).toHaveAccessibleName("Keelstart home");
    await user.tab();
    expect(document.activeElement).toHaveAccessibleName(/Switch company/);
  });

  it("moves between workspace tabs with the arrow keys", async () => {
    const user = userEvent.setup();
    mockApi(loggedIn());
    renderApp(`/app/cases/${CASE.id}/overview`);
    const overview = await screen.findByRole("tab", { name: "Overview" });
    overview.focus();
    await user.keyboard("{ArrowRight}");
    await waitFor(() => expect(location()).toBe(`/app/cases/${CASE.id}/names`));
    expect(screen.getByRole("tab", { name: "Names" })).toHaveFocus();
    await user.keyboard("{End}");
    await waitFor(() => expect(location()).toBe(`/app/cases/${CASE.id}/audit`));
  });

  it("account menu shows the plan badge, Settings and Log out", async () => {
    const user = userEvent.setup();
    const { calls } = mockApi(loggedIn({ "POST /api/auth/logout": { status: 204 } }));
    renderApp("/app");
    await user.click(await screen.findByRole("button", { name: "Account: Alice Chen" }));
    const menu = await screen.findByRole("menu");
    expect(within(menu).getByText("Launch plan")).toBeInTheDocument();
    expect(within(menu).getByRole("menuitem", { name: "Settings" })).toBeInTheDocument();
    await user.click(within(menu).getByRole("menuitem", { name: "Log out" }));
    await waitFor(() => expect(location()).toBe("/login"));
    expect(calls.some((c) => c.method === "POST" && c.url === "/api/auth/logout")).toBe(true);
  });

  it("on phones switches between Chat and Workspace", async () => {
    setViewport(390);
    const user = userEvent.setup();
    mockApi(loggedIn());
    renderApp(`/app/cases/${CASE.id}/overview`);
    const group = await screen.findByRole("radiogroup", { name: "Show" });
    expect(within(group).getByRole("radio", { name: "Chat" })).toBeChecked();
    expect(screen.getByRole("region", { name: "Chat" })).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Workspace" })).not.toBeInTheDocument();
    await user.click(within(group).getByRole("radio", { name: "Workspace" }));
    expect(await screen.findByRole("region", { name: "Workspace" })).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Chat" })).not.toBeInTheDocument();
  });

  it("workspace placeholders show a skeleton while loading", async () => {
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => (release = resolve));
    mockApi(loggedIn({ [`GET /api/cases/${CASE.id}`]: async () => (await gate, json(CASE)) }));
    renderApp(`/app/cases/${CASE.id}/legal`);
    await waitFor(() => expect(document.querySelector('[data-state="loading"]')).not.toBeNull());
    release();
    expect(await screen.findByText("No legal yet")).toBeInTheDocument();
  });
});

describe("demo-mode founder switcher (ADR-0035)", () => {
  it("is hidden and sends no act-as header outside demo mode", async () => {
    const { calls } = mockApi(loggedIn({ "GET /api/config": makeConfig({ demo_mode: false }) }));
    renderApp(`/app/cases/${CASE.id}/overview`);
    await screen.findByRole("tablist", { name: "Workspace views" });
    expect(screen.queryByText("Demo mode")).not.toBeInTheDocument();
    expect(screen.queryByRole("combobox", { name: "Acting as" })).not.toBeInTheDocument();
    expect(calls.every((c) => headerOf(c.init, "X-Act-As-Founder") === null)).toBe(true);
  });

  it("shows 'Demo mode', lets the user pick a founder and sends X-Act-As-Founder", async () => {
    const user = userEvent.setup();
    const { calls } = mockApi(loggedIn({ "GET /api/config": makeConfig({ demo_mode: true }) }));
    renderApp(`/app/cases/${CASE.id}/overview`);
    expect(await screen.findAllByText("Demo mode")).not.toHaveLength(0);
    const select = (await screen.findAllByRole("combobox", { name: "Acting as" }))[0];
    expect(select).toHaveTextContent("Alice Chen");
    await user.click(select);
    await user.click(await screen.findByRole("option", { name: "Bob Diaz" }));
    expect(window.localStorage.getItem(`launch.founder.${CASE.id}`)).toBe("f2");
    await user.click(screen.getByRole("tab", { name: "Names" }));
    await waitFor(() => {
      const caseCalls = calls.filter((c) => c.url.startsWith(`/api/cases/${CASE.id}`));
      expect(caseCalls.some((c) => headerOf(c.init, "X-Act-As-Founder") === "f2")).toBe(true);
    });
    const other = calls.filter((c) => !c.url.startsWith("/api/cases/"));
    expect(other.every((c) => headerOf(c.init, "X-Act-As-Founder") === null)).toBe(true);
  });
});

describe("banners and help (ADR-0035, ADR-0038)", () => {
  it("asks to confirm the email, with a resend button", async () => {
    mockApi(loggedIn({ "GET /api/auth/me": makeMe({ email_verified: false }, { email_verified_at: null }) }));
    renderApp("/app");
    expect(await screen.findByText("Confirm your email to sign documents.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Resend email" })).toBeInTheDocument();
  });

  it("says when payments are simulated", async () => {
    mockApi(loggedIn({ "GET /api/config": makeConfig({ payments_test_mode: true }) }));
    renderApp("/app");
    expect(await screen.findByText("payments are simulated and no card is charged.")).toBeInTheDocument();
  });

  it("says when the AI allowance is used up", async () => {
    mockApi(
      loggedIn({
        "GET /api/billing/subscription": {
          subscription: makeMe().subscription,
          plan: makeConfig().plans[1],
          usage: { ai_messages_used: 2000, ai_messages_limit: 2000, resets_on: "2026-12-01", companies_used: 1, companies_limit: 3 },
          can_switch_plan: true,
        },
      }),
    );
    renderApp("/app");
    expect(await screen.findByText("You've reached your plan's AI allowance.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "See plans" })).toHaveAttribute("href", "/app/settings/billing");
  });

  it("offers Contact support only when a support email is configured", async () => {
    const user = userEvent.setup();
    mockApi(loggedIn({ "GET /api/config": makeConfig({ support_email: "help@example.com" }) }));
    renderApp("/app");
    await user.click(await screen.findByRole("button", { name: "Help" }));
    expect(await screen.findByRole("menuitem", { name: "Contact support" })).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: "Help and questions" })).toBeInTheDocument();
  });

  it("shows only the help link without a support email", async () => {
    const user = userEvent.setup();
    mockApi(loggedIn());
    renderApp("/app");
    await user.click(await screen.findByRole("button", { name: "Help" }));
    expect(await screen.findByRole("menuitem", { name: "Help and questions" })).toBeInTheDocument();
    expect(screen.queryByRole("menuitem", { name: "Contact support" })).not.toBeInTheDocument();
  });
});

describe("placeholder states (ADR-0019)", () => {
  it("companies page: empty state with a way to start", async () => {
    mockApi(loggedIn());
    renderApp("/app");
    expect(await screen.findByText("No companies yet")).toBeInTheDocument();
  });

  it("companies page: friendly error with retry", async () => {
    mockApi(loggedIn({ "GET /api/cases": apiError(500, "internal", "Something went wrong on our side. Please try again.") }));
    renderApp("/app");
    expect(await screen.findByRole("button", { name: "Try again" })).toBeInTheDocument();
    expect(screen.getByText("Something went wrong on our side. Please try again.")).toBeInTheDocument();
  });

  it("sets page titles as '{Page} · Keelstart'", async () => {
    mockApi({});
    renderApp("/pricing");
    await waitFor(() => expect(document.title).toBe("Pricing · Keelstart"));
  });

  it("sets the landing title", async () => {
    mockApi({});
    renderApp("/");
    await waitFor(() => expect(document.title).toBe("Keelstart · Launch your company with a team of AI agents"));
  });
});
