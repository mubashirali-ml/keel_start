/**
 * The typed API client: one function per ADR-0032 endpoint (billing per ADR-0038).
 *
 * - `credentials: "include"` on every call (cookie session, ADR-0026).
 * - Unsafe methods send `X-CSRF-Token` from the `la_csrf` cookie, else the last
 *   `MeView.csrf_token` (ADR-0033).
 * - Timeouts: chat 100 s, everything else 20 s; GET retried twice on network errors,
 *   mutations never (ADR-0023).
 * - Failures become `ApiError` with friendly text and the request id; a 401 (other than
 *   wrong credentials) calls the `onUnauthorized` hook, which sends the browser to
 *   `/login?next=...` (ADR-0035).
 * - In demo mode the acting founder is sent as `X-Act-As-Founder` (ADR-0026).
 */

import { ApiError, errorFromResponse, networkError, reportApiError, timeoutError } from "./errors";
import type {
  AdminCaseRow,
  AdminPage,
  AdminSection,
  AdminUsageRow,
  AdminUserRow,
  AgentProfile,
  AuditEntry,
  BillingInterval,
  BillingOverview,
  CapTable,
  CaseSummary,
  CaseView,
  ChatMessage,
  Document,
  DocumentsOutcome,
  EditOutcome,
  EditRequest,
  GuideView,
  HealthStatus,
  Invite,
  InvitePreview,
  JobRecord,
  JobStatus,
  MeView,
  MemberView,
  NameCandidate,
  OutboxEmailRow,
  Plan,
  PlanId,
  PostMessageResult,
  PublicConfig,
  ReadyStatus,
  SignRequest,
  SiteBuild,
  SiteJobOutcome,
  Subscription,
  SystemInfo,
  UrlResult,
} from "./types";

export const DEFAULT_TIMEOUT_MS = 20_000;
export const CHAT_TIMEOUT_MS = 100_000;
export const GET_RETRIES = 2;
export const CSRF_COOKIE = "la_csrf";
export const CSRF_HEADER = "X-CSRF-Token";
export const ACT_AS_HEADER = "X-Act-As-Founder";
export const REQUEST_ID_HEADER = "X-Request-ID";

type Method = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
const UNSAFE: ReadonlySet<Method> = new Set(["POST", "PUT", "PATCH", "DELETE"]);

export interface ClientConfig {
  fetch: typeof fetch;
  sleep: (ms: number) => Promise<void>;
  /** Called on a 401 that means "no session" (not wrong credentials). */
  onUnauthorized: (error: ApiError) => void;
  /** Founder id to act as for a request path (demo mode only), or null. */
  actAsFounder: (path: string) => string | null;
  /** Base delay before a GET retry; doubles per attempt. */
  retryDelayMs: number;
}

const defaults: ClientConfig = {
  fetch: (...args) => globalThis.fetch(...args),
  sleep: (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
  onUnauthorized: () => undefined,
  actAsFounder: () => null,
  retryDelayMs: 400,
};

let config: ClientConfig = { ...defaults };

/** Overrides parts of the client configuration (the app registers hooks; tests inject `fetch`). */
export function configureClient(patch: Partial<ClientConfig>): void {
  config = { ...config, ...patch };
}

export function resetClient(): void {
  config = { ...defaults };
  csrfFromMe = null;
}

// ---------------------------------------------------------------- CSRF
let csrfFromMe: string | null = null;

/** Keeps the token from the latest `MeView` (login, signup, `GET /api/auth/me`). */
export function rememberCsrfToken(token: string | null | undefined): void {
  csrfFromMe = token || null;
}

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  for (const part of document.cookie.split(";")) {
    const [key, ...rest] = part.trim().split("=");
    if (key === name) return decodeURIComponent(rest.join("="));
  }
  return null;
}

export function csrfToken(): string | null {
  return readCookie(CSRF_COOKIE) || csrfFromMe;
}

// ---------------------------------------------------------------- core request
export interface RequestOptions {
  body?: unknown;
  query?: Record<string, string | number | boolean | null | undefined>;
  timeoutMs?: number;
  signal?: AbortSignal;
  /** Don't redirect to the login page on 401 (e.g. `GET /api/auth/me`). */
  allowAnonymous?: boolean;
  /** Return the raw response body as a Blob (file downloads). */
  blob?: boolean;
}

function buildUrl(path: string, query?: RequestOptions["query"]): string {
  if (!query) return path;
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== null && value !== undefined && value !== "") params.set(key, String(value));
  }
  const qs = params.toString();
  return qs ? `${path}?${qs}` : path;
}

async function parseBody(response: Response): Promise<unknown> {
  if (response.status === 204) return undefined;
  const text = await response.text();
  if (!text) return undefined;
  const type = response.headers.get("content-type") || "";
  if (type.includes("json")) {
    try {
      return JSON.parse(text);
    } catch {
      return undefined;
    }
  }
  return undefined; // HTML error pages from proxies etc. are never shown
}

async function once(method: Method, url: string, options: RequestOptions): Promise<Response> {
  const headers: Record<string, string> = { Accept: options.blob ? "*/*" : "application/json" };
  let body: BodyInit | undefined;
  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.body);
  }
  if (UNSAFE.has(method)) {
    const token = csrfToken();
    if (token) headers[CSRF_HEADER] = token;
  }
  const actAs = config.actAsFounder(url);
  if (actAs) headers[ACT_AS_HEADER] = actAs;

  const controller = new AbortController();
  let timedOut = false;
  const timer = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, options.timeoutMs ?? DEFAULT_TIMEOUT_MS);
  const onCallerAbort = () => controller.abort();
  options.signal?.addEventListener("abort", onCallerAbort);
  try {
    return await config.fetch(url, { method, headers, body, credentials: "include", signal: controller.signal });
  } catch (error) {
    if (timedOut) throw timeoutError();
    if (options.signal?.aborted) throw error; // cancelled by the caller (React Query): not an error to show
    throw networkError();
  } finally {
    clearTimeout(timer);
    options.signal?.removeEventListener("abort", onCallerAbort);
  }
}

/** One API call with the ADR-0023 timeout/retry policy and the error envelope. */
export async function request<T>(method: Method, path: string, options: RequestOptions = {}): Promise<T> {
  const url = buildUrl(path, options.query);
  let response: Response | undefined;
  for (let attempt = 0; ; attempt++) {
    try {
      response = await once(method, url, options);
      break;
    } catch (error) {
      const retryable = method === "GET" && error instanceof ApiError && error.isNetwork && attempt < GET_RETRIES;
      if (!retryable) {
        if (error instanceof ApiError) reportApiError(error);
        throw error;
      }
      await config.sleep(config.retryDelayMs * 2 ** attempt);
    }
  }

  if (!response.ok) {
    const error = errorFromResponse(response.status, await parseBody(response), response.headers.get(REQUEST_ID_HEADER));
    if (error.status === 401 && error.code !== "invalid_credentials" && !options.allowAnonymous) {
      config.onUnauthorized(error);
    }
    if (!(options.allowAnonymous && (error.status === 401 || error.status === 404))) reportApiError(error);
    throw error;
  }
  if (options.blob) {
    const file: DownloadedFile = {
      blob: await response.blob(),
      filename: filenameFrom(response.headers.get("content-disposition")),
    };
    return file as T;
  }
  return (await parseBody(response)) as T;
}

/** A downloaded file and the name the server suggested. */
export interface DownloadedFile {
  blob: Blob;
  filename: string | null;
}

function filenameFrom(disposition: string | null): string | null {
  if (!disposition) return null;
  const match = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(disposition);
  return match ? decodeURIComponent(match[1]) : null;
}

const download = (path: string) => request<DownloadedFile>("GET", path, { blob: true });

const enc = encodeURIComponent;
const c = (caseId: string) => `/api/cases/${enc(caseId)}`;

// ---------------------------------------------------------------- public
export const getHealth = () => request<HealthStatus>("GET", "/api/health");
export const getReady = () => request<ReadyStatus>("GET", "/api/ready");
export const getConfig = () => request<PublicConfig>("GET", "/api/config", { allowAnonymous: true });
export const listAgents = () => request<AgentProfile[]>("GET", "/api/agents", { allowAnonymous: true });

// ---------------------------------------------------------------- auth (ADR-0026)
export interface SignupBody {
  email: string;
  password: string;
  full_name: string;
  accept_terms: true;
}
export const signup = (body: SignupBody) => request<MeView>("POST", "/api/auth/signup", { body, allowAnonymous: true });
export const login = (body: { email: string; password: string }) =>
  request<MeView>("POST", "/api/auth/login", { body, allowAnonymous: true });
export const logout = () => request<void>("POST", "/api/auth/logout", { allowAnonymous: true });
export const getMe = () => request<MeView>("GET", "/api/auth/me", { allowAnonymous: true });
export const verifyEmail = (token: string) =>
  request<MeView>("POST", "/api/auth/verify-email", { body: { token }, allowAnonymous: true });
export const resendVerification = () => request<void>("POST", "/api/auth/resend-verification");
export const forgotPassword = (email: string) =>
  request<void>("POST", "/api/auth/forgot-password", { body: { email }, allowAnonymous: true });
export const resetPassword = (token: string, password: string) =>
  request<void>("POST", "/api/auth/reset-password", { body: { token, password }, allowAnonymous: true });

// ---------------------------------------------------------------- account
export const updateAccount = (body: { full_name: string }) => request<MeView>("PATCH", "/api/account", { body });
export const changePassword = (body: { current_password: string; new_password: string }) =>
  request<void>("POST", "/api/account/password", { body });
export const exportAccount = () => download("/api/account/export");
export const deleteAccount = (body: { password: string; confirm: "DELETE" }) =>
  request<void>("DELETE", "/api/account", { body });

// ---------------------------------------------------------------- team
export const listMembers = (caseId: string) => request<MemberView[]>("GET", `${c(caseId)}/members`);
export const listInvites = (caseId: string) => request<Invite[]>("GET", `${c(caseId)}/invites`);
export const createInvite = (caseId: string, body: { email: string; founder_id?: string | null }) =>
  request<Invite>("POST", `${c(caseId)}/invites`, { body });
export const revokeInvite = (caseId: string, inviteId: string) =>
  request<void>("DELETE", `${c(caseId)}/invites/${enc(inviteId)}`);
export const removeMember = (caseId: string, userId: string) =>
  request<void>("DELETE", `${c(caseId)}/members/${enc(userId)}`);
export const getInvitePreview = (token: string) =>
  request<InvitePreview>("GET", `/api/invites/${enc(token)}`, { allowAnonymous: true });
export const acceptInvite = (token: string) => request<{ case_id: string }>("POST", `/api/invites/${enc(token)}/accept`);

// ---------------------------------------------------------------- cases
export const createCase = () => request<CaseView>("POST", "/api/cases");
export const listCases = () => request<CaseSummary[]>("GET", "/api/cases");
export const getCase = (caseId: string) => request<CaseView>("GET", c(caseId));
export const deleteCase = (caseId: string) => request<void>("DELETE", c(caseId));
export const listMessages = (caseId: string, afterSeq?: number | null) =>
  request<ChatMessage[]>("GET", `${c(caseId)}/messages`, { query: { after_seq: afterSeq } });
export const postMessage = (caseId: string, text: string) =>
  request<PostMessageResult>("POST", `${c(caseId)}/messages`, { body: { text }, timeoutMs: CHAT_TIMEOUT_MS });
export const listNames = (caseId: string) => request<NameCandidate[]>("GET", `${c(caseId)}/names`);
export const chooseName = (caseId: string, body: { name: string; domain?: string | null }) =>
  request<CaseView>("POST", `${c(caseId)}/names/choose`, { body });
export const recheckNames = (caseId: string) => request<NameCandidate[]>("POST", `${c(caseId)}/names/recheck`);
export const getGuide = (caseId: string) => request<GuideView>("GET", `${c(caseId)}/guide`);
export const setGuideItem = (caseId: string, itemId: string, done: boolean) =>
  request<GuideView>("PUT", `${c(caseId)}/guide/items/${enc(itemId)}`, { body: { done } });
export const listJobs = (caseId: string) => request<JobRecord[]>("GET", `${c(caseId)}/jobs`);
export const getJob = (caseId: string, jobId: string) => request<JobRecord>("GET", `${c(caseId)}/jobs/${enc(jobId)}`);

// ---------------------------------------------------------------- legal
export const getCapTable = (caseId: string) => request<CapTable>("GET", `${c(caseId)}/cap-table`);
export const downloadCapTableCsv = (caseId: string) => download(`${c(caseId)}/cap-table.csv`);
export const downloadCapTableXlsx = (caseId: string) => download(`${c(caseId)}/cap-table.xlsx`);
export const listDocuments = (caseId: string) => request<Document[]>("GET", `${c(caseId)}/documents`);
export const generateDocuments = (caseId: string) =>
  request<DocumentsOutcome>("POST", `${c(caseId)}/documents/generate`);
export const getDocument = (caseId: string, docId: string) =>
  request<Document>("GET", `${c(caseId)}/documents/${enc(docId)}`);
export const signDocument = (caseId: string, docId: string, body: SignRequest) =>
  request<Document>("POST", `${c(caseId)}/documents/${enc(docId)}/sign`, { body });
export const editDocument = (caseId: string, docId: string, body: EditRequest) =>
  request<EditOutcome>("POST", `${c(caseId)}/documents/${enc(docId)}/edit`, { body });
export const downloadDocumentPdf = (caseId: string, docId: string) =>
  download(`${c(caseId)}/documents/${enc(docId)}/pdf`);
export const downloadDocumentDocx = (caseId: string, docId: string) =>
  download(`${c(caseId)}/documents/${enc(docId)}/docx`);
export const getAudit = (caseId: string) => request<AuditEntry[]>("GET", `${c(caseId)}/audit`);

// ---------------------------------------------------------------- website
export const getWebsite = (caseId: string) => request<SiteBuild | null>("GET", `${c(caseId)}/website`);
export const buildWebsite = (caseId: string, changeRequest?: string | null) =>
  request<SiteJobOutcome>("POST", `${c(caseId)}/website/build`, {
    body: changeRequest ? { change_request: changeRequest } : {},
  });
export const deployWebsite = (caseId: string, overrideQa = false) =>
  request<SiteJobOutcome>("POST", `${c(caseId)}/website/deploy`, { body: { override_qa: overrideQa } });
/** URL for the sandboxed preview iframe (same origin, cookie session). */
export const websitePreviewUrl = (caseId: string, path = "index.html") =>
  `${c(caseId)}/website/preview/${path.split("/").map(enc).join("/")}`;
export const downloadWebsite = (caseId: string) => download(`${c(caseId)}/website/download`);

// ---------------------------------------------------------------- billing (ADR-0038)
export const listPlans = () => request<Plan[]>("GET", "/api/billing/plans", { allowAnonymous: true });
export const getSubscription = () => request<BillingOverview>("GET", "/api/billing/subscription");
export const startCheckout = (body: { plan: PlanId; interval: BillingInterval }) =>
  request<UrlResult>("POST", "/api/billing/checkout", { body });
export const openPortal = () => request<UrlResult>("POST", "/api/billing/portal");
export const changePlan = (body: { plan: PlanId; interval: BillingInterval }) =>
  request<Subscription>("POST", "/api/billing/change-plan", { body });
export const completeTestCheckout = (sessionId: string) =>
  request<void>("POST", `/api/billing/test-checkout/${enc(sessionId)}/complete`);

// ---------------------------------------------------------------- admin (ADR-0034)
export const adminUsers = (params: { query?: string; page?: number; plan?: PlanId | null } = {}) =>
  request<AdminPage<AdminUserRow>>("GET", "/api/admin/users", { query: params });
export const adminCases = (params: { query?: string; page?: number } = {}) =>
  request<AdminPage<AdminCaseRow>>("GET", "/api/admin/cases", { query: params });
export const adminUsage = (params: { month?: string } = {}) =>
  request<AdminUsageRow[]>("GET", "/api/admin/usage", { query: params });
export const adminJobs = (params: { status?: JobStatus | null; page?: number } = {}) =>
  request<AdminPage<JobRecord>>("GET", "/api/admin/jobs", { query: params });
export const adminEmails = (params: { status?: string | null; page?: number } = {}) =>
  request<AdminPage<OutboxEmailRow>>("GET", "/api/admin/emails", { query: params });
export const adminSystem = () => request<SystemInfo>("GET", "/api/admin/system");
export const adminRetryJob = (jobId: string) => request<JobRecord>("POST", `/api/admin/jobs/${enc(jobId)}/retry`);

/** Every admin read endpoint, by section (used by the admin area). */
export const ADMIN_ENDPOINTS: Record<AdminSection, string> = {
  users: "/api/admin/users",
  companies: "/api/admin/cases",
  usage: "/api/admin/usage",
  jobs: "/api/admin/jobs",
  emails: "/api/admin/emails",
  system: "/api/admin/system",
};

/** The case id in an API path (`/api/cases/{id}/...`), or null. */
export function caseIdFromPath(path: string): string | null {
  const match = /^\/api\/cases\/([^/?#]+)/.exec(path);
  return match ? decodeURIComponent(match[1]) : null;
}
