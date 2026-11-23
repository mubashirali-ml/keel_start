import * as api from "./client";
import { ApiError, NETWORK_MESSAGE, TIMEOUT_MESSAGE, getLastApiError } from "./errors";
import { supportMailto } from "./support";
import { apiError, headerOf, json, mockApi } from "@/test/mockFetch";

describe("API client (ADR-0032, ADR-0033, ADR-0023)", () => {
  it("sends credentials with every call and parses JSON", async () => {
    const { calls } = mockApi({ "GET /api/cases": [{ id: "case_0123456789ab" }] });
    const cases = await api.listCases();
    expect(cases).toEqual([{ id: "case_0123456789ab" }]);
    expect(calls[0].init.credentials).toBe("include");
  });

  it("sends X-CSRF-Token from the la_csrf cookie on unsafe methods only", async () => {
    document.cookie = "la_csrf=cookie-token; path=/";
    const { calls } = mockApi({ "POST /api/cases": json({ id: "case_x" }, 201), "GET /api/cases": [] });
    await api.createCase();
    await api.listCases();
    expect(headerOf(calls[0].init, "X-CSRF-Token")).toBe("cookie-token");
    expect(headerOf(calls[1].init, "X-CSRF-Token")).toBeNull();
  });

  it("falls back to MeView.csrf_token when there is no cookie", async () => {
    const { calls } = mockApi({ "DELETE /api/cases/case_x": { status: 204 } });
    api.rememberCsrfToken("token-from-me");
    await api.deleteCase("case_x");
    expect(headerOf(calls[0].init, "X-CSRF-Token")).toBe("token-from-me");
    expect(calls[0].init.method).toBe("DELETE");
  });

  it("turns the error envelope into ApiError with the friendly message and request id", async () => {
    mockApi({
      "POST /api/cases/c/documents/d/sign": apiError(409, "stale_version", "This document changed. Please review the new version.", { current: 3 }, "req-0001abcd"),
    });
    const error = await api
      .signDocument("c", "d", { version: 2, content_sha256: "x", typed_name: "Alice Chen", consent: true })
      .catch((e) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ code: "stale_version", status: 409, requestId: "req-0001abcd", details: { current: 3 } });
    expect(error.message).toBe("This document changed. Please review the new version.");
    expect(getLastApiError()?.requestId).toBe("req-0001abcd");
  });

  it("never surfaces raw bodies: HTML error pages become a friendly 500", async () => {
    mockApi({ "GET /api/cases": () => ({ status: 502, body: undefined, headers: { "content-type": "text/html", "X-Request-ID": "req-proxy-1" } }) });
    const error = (await api.listCases().catch((e) => e)) as ApiError;
    expect(error.status).toBe(502);
    expect(error.message).toMatch(/isn't responding/);
    expect(error.requestId).toBe("req-proxy-1");
  });

  it("network failure becomes a friendly ApiError; GET is retried twice", async () => {
    const fetchMock = vi.fn(async () => {
      throw new TypeError("Failed to fetch");
    });
    const sleep = vi.fn(async () => undefined);
    api.configureClient({ fetch: fetchMock as unknown as typeof fetch, sleep });
    const error = (await api.listCases().catch((e) => e)) as ApiError;
    expect(error.code).toBe("network_error");
    expect(error.message).toBe(NETWORK_MESSAGE);
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(sleep).toHaveBeenCalledTimes(2);
  });

  it("a GET that recovers on retry succeeds", async () => {
    let n = 0;
    const fetchMock = vi.fn(async () => {
      n += 1;
      if (n === 1) throw new TypeError("Failed to fetch");
      return new Response(JSON.stringify([]), { status: 200, headers: { "content-type": "application/json" } });
    });
    api.configureClient({ fetch: fetchMock as unknown as typeof fetch, sleep: async () => undefined });
    await expect(api.listCases()).resolves.toEqual([]);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("mutations are never retried", async () => {
    const fetchMock = vi.fn(async () => {
      throw new TypeError("Failed to fetch");
    });
    api.configureClient({ fetch: fetchMock as unknown as typeof fetch, sleep: async () => undefined });
    await expect(api.postMessage("c", "hello")).rejects.toMatchObject({ code: "network_error" });
    await expect(api.createCase()).rejects.toMatchObject({ code: "network_error" });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  function hangingFetch() {
    return vi.fn(
      (_url: RequestInfo | URL, init?: RequestInit) =>
        new Promise<Response>((_resolve, reject) => {
          init?.signal?.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError")));
        }),
    );
  }

  it("times out other calls after 20 s with a friendly error", async () => {
    vi.useFakeTimers();
    const fetchMock = hangingFetch();
    api.configureClient({ fetch: fetchMock as unknown as typeof fetch });
    const pending = api.getCase("c").catch((e) => e);
    await vi.advanceTimersByTimeAsync(19_999);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(2);
    const error = (await pending) as ApiError;
    expect(error.code).toBe("timeout");
    expect(error.message).toBe(TIMEOUT_MESSAGE);
    expect(fetchMock).toHaveBeenCalledTimes(1); // timeouts are not retried
  });

  it("gives chat 100 s before timing out", async () => {
    vi.useFakeTimers();
    api.configureClient({ fetch: hangingFetch() as unknown as typeof fetch });
    let settled = false;
    const pending = api.postMessage("c", "hello").catch((e) => {
      settled = true;
      return e;
    });
    await vi.advanceTimersByTimeAsync(99_000);
    expect(settled).toBe(false);
    await vi.advanceTimersByTimeAsync(1_001);
    expect(((await pending) as ApiError).code).toBe("timeout");
    expect(api.CHAT_TIMEOUT_MS).toBe(100_000);
    expect(api.DEFAULT_TIMEOUT_MS).toBe(20_000);
  });

  it("calls onUnauthorized on a 401, but not for wrong credentials or the session probe", async () => {
    const onUnauthorized = vi.fn();
    mockApi({
      "GET /api/cases": apiError(401, "auth_required", "Please log in to continue."),
      "POST /api/auth/login": apiError(401, "invalid_credentials", "That email and password don't match."),
      "GET /api/auth/me": apiError(401, "auth_required", "Please log in to continue."),
      "POST /api/account/password": apiError(401, "invalid_credentials", "Your current password isn't right."),
    });
    api.configureClient({ onUnauthorized });
    await api.listCases().catch(() => undefined);
    expect(onUnauthorized).toHaveBeenCalledTimes(1);
    await api.login({ email: "a@example.com", password: "x" }).catch(() => undefined);
    await api.getMe().catch(() => undefined);
    await api.changePassword({ current_password: "x", new_password: "y" }).catch(() => undefined);
    expect(onUnauthorized).toHaveBeenCalledTimes(1);
  });

  it("sends X-Act-As-Founder only for the registered company", async () => {
    const { calls } = mockApi({ "GET /api/cases/case_a": {}, "GET /api/cases/case_b": {}, "GET /api/cases": [] });
    api.configureClient({ actAsFounder: (path) => (api.caseIdFromPath(path) === "case_a" ? "f2" : null) });
    await api.getCase("case_a");
    await api.getCase("case_b");
    await api.listCases();
    expect(calls.map((c) => headerOf(c.init, "X-Act-As-Founder"))).toEqual(["f2", null, null]);
  });

  it("has one function per ADR-0032 / ADR-0038 endpoint with the right method and path", async () => {
    const { calls } = mockApi({});
    const sign = { version: 1, content_sha256: "h", typed_name: "A", consent: true as const };
    const run = [
      api.getHealth(), api.getReady(), api.getConfig(), api.listAgents(),
      api.signup({ email: "e", password: "p", full_name: "n", accept_terms: true }), api.login({ email: "e", password: "p" }),
      api.logout(), api.getMe(), api.verifyEmail("t"), api.resendVerification(), api.forgotPassword("e"), api.resetPassword("t", "p"),
      api.updateAccount({ full_name: "n" }), api.changePassword({ current_password: "a", new_password: "b" }), api.exportAccount(),
      api.deleteAccount({ password: "p", confirm: "DELETE" }),
      api.listMembers("c"), api.listInvites("c"), api.createInvite("c", { email: "e" }), api.revokeInvite("c", "i"), api.removeMember("c", "u"),
      api.getInvitePreview("tok"), api.acceptInvite("tok"),
      api.createCase(), api.listCases(), api.getCase("c"), api.deleteCase("c"), api.listMessages("c", 4), api.postMessage("c", "hi"),
      api.listNames("c"), api.chooseName("c", { name: "Acme" }), api.recheckNames("c"), api.getGuide("c"), api.setGuideItem("c", "83b-mail", true),
      api.listJobs("c"), api.getJob("c", "j"),
      api.getCapTable("c"), api.downloadCapTableCsv("c"), api.downloadCapTableXlsx("c"), api.listDocuments("c"), api.generateDocuments("c"),
      api.getDocument("c", "d"), api.signDocument("c", "d", sign), api.editDocument("c", "d", { ...sign, content: "x" }),
      api.downloadDocumentPdf("c", "d"), api.downloadDocumentDocx("c", "d"), api.getAudit("c"),
      api.getWebsite("c"), api.buildWebsite("c", "add pricing"), api.deployWebsite("c", true), api.downloadWebsite("c"),
      api.listPlans(), api.getSubscription(), api.startCheckout({ plan: "launch", interval: "month" }), api.openPortal(),
      api.changePlan({ plan: "team", interval: "year" }), api.completeTestCheckout("cs_1"),
      api.adminUsers({ plan: "team", page: 2 }), api.adminCases({ query: "acme" }), api.adminUsage({ month: "2026-11" }),
      api.adminJobs({ status: "failed" }), api.adminEmails({ status: "failed" }), api.adminSystem(), api.adminRetryJob("j"),
    ];
    await Promise.allSettled(run);
    const seen = calls.map((c) => `${c.method} ${c.url}`);
    expect(seen).toEqual([
      "GET /api/health", "GET /api/ready", "GET /api/config", "GET /api/agents",
      "POST /api/auth/signup", "POST /api/auth/login", "POST /api/auth/logout", "GET /api/auth/me", "POST /api/auth/verify-email",
      "POST /api/auth/resend-verification", "POST /api/auth/forgot-password", "POST /api/auth/reset-password",
      "PATCH /api/account", "POST /api/account/password", "GET /api/account/export", "DELETE /api/account",
      "GET /api/cases/c/members", "GET /api/cases/c/invites", "POST /api/cases/c/invites", "DELETE /api/cases/c/invites/i",
      "DELETE /api/cases/c/members/u", "GET /api/invites/tok", "POST /api/invites/tok/accept",
      "POST /api/cases", "GET /api/cases", "GET /api/cases/c", "DELETE /api/cases/c", "GET /api/cases/c/messages?after_seq=4",
      "POST /api/cases/c/messages", "GET /api/cases/c/names", "POST /api/cases/c/names/choose", "POST /api/cases/c/names/recheck",
      "GET /api/cases/c/guide", "PUT /api/cases/c/guide/items/83b-mail", "GET /api/cases/c/jobs", "GET /api/cases/c/jobs/j",
      "GET /api/cases/c/cap-table", "GET /api/cases/c/cap-table.csv", "GET /api/cases/c/cap-table.xlsx", "GET /api/cases/c/documents",
      "POST /api/cases/c/documents/generate", "GET /api/cases/c/documents/d", "POST /api/cases/c/documents/d/sign",
      "POST /api/cases/c/documents/d/edit", "GET /api/cases/c/documents/d/pdf", "GET /api/cases/c/documents/d/docx", "GET /api/cases/c/audit",
      "GET /api/cases/c/website", "POST /api/cases/c/website/build", "POST /api/cases/c/website/deploy", "GET /api/cases/c/website/download",
      "GET /api/billing/plans", "GET /api/billing/subscription", "POST /api/billing/checkout", "POST /api/billing/portal",
      "POST /api/billing/change-plan", "POST /api/billing/test-checkout/cs_1/complete",
      "GET /api/admin/users?plan=team&page=2", "GET /api/admin/cases?query=acme", "GET /api/admin/usage?month=2026-11",
      "GET /api/admin/jobs?status=failed", "GET /api/admin/emails?status=failed", "GET /api/admin/system", "POST /api/admin/jobs/j/retry",
    ]);
    expect(api.websitePreviewUrl("c", "about.html")).toBe("/api/cases/c/website/preview/about.html");
  });

  it("returns downloads as a blob with the server's file name", async () => {
    mockApi({
      "GET /api/cases/c/cap-table.csv": () => ({ status: 200, body: "a,b", headers: { "content-type": "text/csv", "content-disposition": 'attachment; filename="cap-table.csv"' } }),
    });
    const file = await api.downloadCapTableCsv("c");
    expect(file.filename).toBe("cap-table.csv");
    expect(file.blob).toBeInstanceOf(Blob);
  });
});

describe("Contact support mailto (ADR-0038)", () => {
  it("starts the subject with the plan name and quotes the last request id", () => {
    const error = new ApiError({ code: "internal", status: 500, message: "Something went wrong on our side.", requestId: "req-42abcdef" });
    const href = supportMailto("help@example.com", "Team", error);
    const url = new URL(href);
    expect(url.protocol).toBe("mailto:");
    expect(url.pathname).toBe("help@example.com");
    const subject = decodeURIComponent(url.searchParams.get("subject")!);
    expect(subject.startsWith("[Team] ")).toBe(true);
    expect(subject).toContain("req-42abcdef");
    expect(decodeURIComponent(url.searchParams.get("body")!)).toContain("Request id: req-42abcdef");
    expect(decodeURIComponent(new URL(supportMailto("help@example.com", "Free", null)).searchParams.get("subject")!)).toBe("[Free] Help request");
  });
});
