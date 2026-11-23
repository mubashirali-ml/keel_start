/**
 * A route-table `fetch` mock: `mockApi({"GET /api/auth/me": me, "GET /api/cases/x": notFound()})`.
 * Unlisted calls get the backend's JSON 404 envelope (like routes that don't exist yet).
 */
import { vi } from "vitest";

import { configureClient } from "@/api/client";

export interface MockResponse {
  status: number;
  body?: unknown;
  headers?: Record<string, string>;
}

export type Handler = MockResponse | unknown | ((init: RequestInit, url: string) => MockResponse | unknown | Promise<unknown>);

export function json(body: unknown, status = 200, headers: Record<string, string> = {}): MockResponse {
  return { status, body, headers };
}

export function apiError(status: number, code: string, message: string, details: Record<string, unknown> = {}, requestId = "req-test-1234"): MockResponse {
  return { status, body: { error: { code, message, details, request_id: requestId } }, headers: { "X-Request-ID": requestId } };
}

export const notFound = () => apiError(404, "not_found", "We couldn't find that.");
export const unauthorized = () => apiError(401, "auth_required", "Please log in to continue.");

function isMock(value: unknown): value is MockResponse {
  return typeof value === "object" && value !== null && "status" in value && typeof (value as MockResponse).status === "number";
}

export function toResponse(value: MockResponse): Response {
  const headers = new Headers({ "content-type": "application/json", ...(value.headers ?? {}) });
  const text = value.body === undefined ? "" : JSON.stringify(value.body);
  return new Response(value.status === 204 ? null : text, { status: value.status, headers });
}

export function mockApi(routes: Record<string, Handler>) {
  const calls: { method: string; url: string; init: RequestInit }[] = [];
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init: RequestInit = {}) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
    const method = (init.method ?? "GET").toUpperCase();
    calls.push({ method, url, init });
    const path = url.split("?")[0];
    const handler = routes[`${method} ${url}`] ?? routes[`${method} ${path}`];
    if (handler === undefined) return toResponse(notFound());
    const value = typeof handler === "function" ? await (handler as (i: RequestInit, u: string) => unknown)(init, url) : handler;
    return toResponse(isMock(value) ? value : json(value));
  });
  configureClient({ fetch: fetchMock as unknown as typeof fetch, sleep: async () => undefined });
  return { fetchMock, calls };
}

export function headerOf(init: RequestInit, name: string): string | null {
  const headers = new Headers(init.headers);
  return headers.get(name);
}
