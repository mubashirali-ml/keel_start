/**
 * `ApiError` (ADR-0035): every failed call becomes one, with friendly English, the error
 * code, the HTTP status and the request id the founder can quote to support (ADR-0034).
 * Raw JSON, stack traces and HTML error pages never reach the UI.
 */

export const NETWORK_MESSAGE = "We couldn't reach the server. Check your connection and try again.";
export const TIMEOUT_MESSAGE = "This is taking longer than expected. Please try again in a moment.";
export const INTERNAL_MESSAGE = "Something went wrong on our side. Please try again.";

/** Friendly fallbacks when a response carries no envelope message. */
const STATUS_MESSAGES: Record<number, string> = {
  400: "That request couldn't be completed. Please check the details and try again.",
  401: "Please log in to continue.",
  402: "This is part of a paid plan.",
  403: "You don't have access to that.",
  404: "We couldn't find that.",
  409: "That changed while you were working. Refresh and try again.",
  413: "That's too large to send.",
  422: "Some of the details you sent aren't valid. Please check them and try again.",
  429: "Too many attempts. Please wait a moment and try again.",
  502: "A service we depend on isn't responding. Please try again in a minute.",
  503: "We're temporarily unavailable. Please try again in a minute.",
  504: TIMEOUT_MESSAGE,
};

const STATUS_CODES: Record<number, string> = {
  400: "invalid_request",
  401: "auth_required",
  402: "plan_required",
  403: "forbidden",
  404: "not_found",
  409: "conflict",
  422: "invalid_request",
  429: "rate_limited",
  502: "external_service",
  503: "temporarily_unavailable",
  504: "timeout",
};

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly requestId: string | null;
  readonly details: Record<string, unknown>;

  constructor(init: {
    code: string;
    message: string;
    status: number;
    requestId?: string | null;
    details?: Record<string, unknown>;
  }) {
    super(init.message);
    this.name = "ApiError";
    this.code = init.code;
    this.status = init.status;
    this.requestId = init.requestId ?? null;
    this.details = init.details ?? {};
  }

  /** No response at all (offline, DNS, connection refused). */
  get isNetwork(): boolean {
    return this.code === "network_error";
  }

  get isNotFound(): boolean {
    return this.status === 404;
  }

  get isAuth(): boolean {
    return this.status === 401;
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}

export function networkError(): ApiError {
  return new ApiError({ code: "network_error", message: NETWORK_MESSAGE, status: 0 });
}

export function timeoutError(): ApiError {
  return new ApiError({ code: "timeout", message: TIMEOUT_MESSAGE, status: 0 });
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** Builds the `ApiError` for a non-2xx response from its (possibly missing) envelope. */
export function errorFromResponse(status: number, body: unknown, headerRequestId: string | null): ApiError {
  const envelope = isRecord(body) && isRecord(body.error) ? body.error : null;
  const code = typeof envelope?.code === "string" && envelope.code ? envelope.code : STATUS_CODES[status] ?? (status >= 500 ? "internal" : "error");
  const raw = typeof envelope?.message === "string" ? envelope.message.trim() : "";
  // Server messages are founder-facing English (ADR-0008); anything that looks like data is not shown.
  const looksRaw = raw.startsWith("{") || raw.startsWith("[") || raw.includes("Traceback");
  const message = raw && !looksRaw ? raw : STATUS_MESSAGES[status] ?? (status >= 500 ? INTERNAL_MESSAGE : STATUS_MESSAGES[400]);
  const requestId = (typeof envelope?.request_id === "string" && envelope.request_id) || headerRequestId || null;
  const details = isRecord(envelope?.details) ? envelope.details : {};
  return new ApiError({ code, message, status, requestId, details });
}

/** Friendly text for any thrown value (never raw JSON or a stack trace). */
export function friendlyMessage(error: unknown): string {
  if (isApiError(error)) return error.message;
  return INTERNAL_MESSAGE;
}

// ---------------------------------------------------------------- last error (support mailto, ADR-0038)
type Listener = (error: ApiError) => void;
let lastError: ApiError | null = null;
const listeners = new Set<Listener>();

/** Records an error so "Contact support" can quote its request id and banners can react. */
export function reportApiError(error: ApiError): void {
  lastError = error;
  listeners.forEach((listener) => listener(error));
}

export function getLastApiError(): ApiError | null {
  return lastError;
}

export function onApiError(listener: Listener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** Test helper. */
export function resetLastApiError(): void {
  lastError = null;
}
