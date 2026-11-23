/// <reference types="vitest" />
import react from "@vitejs/plugin-react";
import { defineConfig, type Plugin } from "vite";

import { BRAND_FALLBACK_NAME, TAGLINE, disclaimerLine, landingTitle } from "./src/brand/brand";

/** Fills the brand placeholders of index.html from src/brand (ADR-0041: one source). */
function brandHtml(): Plugin {
  const values: Record<string, string> = {
    "%BRAND_NAME%": BRAND_FALLBACK_NAME,
    "%BRAND_TAGLINE%": TAGLINE,
    "%BRAND_TITLE%": landingTitle(BRAND_FALLBACK_NAME),
    "%BRAND_DISCLAIMER%": disclaimerLine(BRAND_FALLBACK_NAME),
  };
  return {
    name: "brand-html",
    transformIndexHtml(html) {
      return Object.entries(values).reduce((out, [key, value]) => out.split(key).join(value), html);
    },
  };
}

export default defineConfig({
  plugins: [react(), brandHtml()],
  resolve: {
    // `@/app` is the app/ folder, not App.tsx (case-insensitive file systems).
    alias: [
      { find: /^@\/app$/, replacement: "/src/app/index.ts" },
      { find: /^@\//, replacement: "/src/" },
    ],
  },
  server: {
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
  build: {
    sourcemap: false,
    chunkSizeWarningLimit: 600,
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    // Token tests read tokens.css / index.css as raw text.
    css: { include: [/\.css/] },
    restoreMocks: true,
  },
});
