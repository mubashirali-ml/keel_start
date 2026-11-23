import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import indexHtml from "/index.html?raw";
import themeInit from "/public/theme-init.js?raw";
import { setViewport } from "@/test/media";

import { ThemeProvider, ThemeToggle } from "./theme";

// The production build, when present (verify.sh builds before testing).
const DIST = import.meta.glob("/dist/**/*.{html,js}", { query: "?raw", import: "default", eager: true }) as Record<string, string>;

function runThemeInit() {
  // The same file the browser loads before first paint.
  new Function(themeInit)();
}

/** Every <script> tag in an HTML document; inline ones have no src. */
function scripts(html: string) {
  return Array.from(html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/gi)).map((m) => ({ attrs: m[1], body: m[2].trim() }));
}

describe("theme (ADR-0019)", () => {
  it("follows the system by default and persists the toggle under launch.theme", async () => {
    const user = userEvent.setup();
    render(
      <ThemeProvider>
        <ThemeToggle />
      </ThemeProvider>,
    );
    expect(document.documentElement).not.toHaveClass("dark");
    await user.click(screen.getByRole("button", { name: "Theme: System. Change theme" }));
    await user.click(await screen.findByRole("menuitemradio", { name: "Dark" }));
    expect(document.documentElement).toHaveClass("dark");
    expect(window.localStorage.getItem("launch.theme")).toBe("dark");
  });

  it("restores the saved theme on the next load", () => {
    window.localStorage.setItem("launch.theme", "dark");
    render(
      <ThemeProvider>
        <ThemeToggle />
      </ThemeProvider>,
    );
    expect(document.documentElement).toHaveClass("dark");
    expect(screen.getByRole("button", { name: "Theme: Dark. Change theme" })).toBeInTheDocument();
  });

  it("follows a dark system theme when set to system", async () => {
    setViewport(1280, { dark: true });
    render(<ThemeProvider>{null}</ThemeProvider>);
    await waitFor(() => expect(document.documentElement).toHaveClass("dark"));
  });

  describe("public/theme-init.js (no flash of the wrong theme)", () => {
    it("applies a saved dark theme before React loads", () => {
      window.localStorage.setItem("launch.theme", "dark");
      runThemeInit();
      expect(document.documentElement).toHaveClass("dark");
    });

    it("applies a saved light theme even on a dark system", () => {
      setViewport(1280, { dark: true });
      window.localStorage.setItem("launch.theme", "light");
      runThemeInit();
      expect(document.documentElement).not.toHaveClass("dark");
    });

    it("follows the system when nothing is saved", () => {
      setViewport(1280, { dark: true });
      runThemeInit();
      expect(document.documentElement).toHaveClass("dark");
    });
  });
});

describe("no inline scripts (ADR-0033 CSP: script-src 'self')", () => {
  it("index.html loads theme-init.js from a file, first in <head>, and has no inline script", () => {
    const all = scripts(indexHtml);
    expect(all.length).toBeGreaterThanOrEqual(2);
    for (const s of all) {
      expect(s.attrs).toMatch(/\bsrc=/);
      expect(s.body).toBe("");
    }
    expect(all[0].attrs).toContain('src="/theme-init.js"');
    expect(indexHtml.indexOf("/theme-init.js")).toBeLessThan(indexHtml.indexOf("</head>"));
    expect(indexHtml).not.toMatch(/\son[a-z]+=/i); // no inline event handlers either
  });

  it("the build output has no inline scripts", () => {
    const html = Object.entries(DIST).filter(([path]) => path.endsWith(".html"));
    for (const [path, text] of html) {
      for (const s of scripts(text)) {
        expect(s.attrs, path).toMatch(/\bsrc=/);
        expect(s.body, path).toBe("");
      }
      expect(text, path).not.toMatch(/\son[a-z]+=/i);
    }
  });
});
