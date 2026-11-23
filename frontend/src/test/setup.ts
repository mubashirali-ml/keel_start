import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach, beforeEach, vi } from "vitest";

import { resetClient } from "@/api/client";
import { resetLastApiError } from "@/api/errors";

import { setViewport } from "./media";

// jsdom lacks these browser APIs that Radix and our hooks use.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver ??= ResizeObserverStub as unknown as typeof ResizeObserver;
Element.prototype.scrollIntoView ??= function scrollIntoView() {};
Element.prototype.hasPointerCapture ??= () => false;
Element.prototype.releasePointerCapture ??= () => undefined;
window.HTMLElement.prototype.scrollTo ??= function scrollTo() {};

beforeEach(() => {
  setViewport(1280);
  window.localStorage.clear();
  document.documentElement.className = "";
  document.cookie = "la_csrf=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/";
});

afterEach(() => {
  cleanup();
  resetClient();
  resetLastApiError();
  vi.useRealTimers();
});
