import tokensCss from "./tokens.css?raw";
import { AGENT_ACCENTS, CONTRAST_PAIRS, contrastRatio, parseTokens, toHsl } from "./contrast";

const tokens = parseTokens(tokensCss);
const SOURCES = import.meta.glob("/src/**/*.{ts,tsx,css}", { query: "?raw", import: "default", eager: true }) as Record<string, string>;

const REQUIRED = [
  "bg",
  "surface",
  "surface-raised",
  "border",
  "border-strong",
  "text",
  "text-muted",
  "text-subtle",
  "primary",
  "primary-fg",
  "success",
  "success-fg",
  "warning",
  "warning-fg",
  "danger",
  "danger-fg",
  "info",
  "info-fg",
  "focus-ring",
  ...AGENT_ACCENTS,
];

describe("design tokens (ADR-0019, ADR-0041)", () => {
  it("defines every color token for light and dark", () => {
    for (const name of REQUIRED) {
      expect(tokens.light[name], `light ${name}`).toBeDefined();
      expect(tokens.dark[name], `dark ${name}`).toBeDefined();
    }
    expect(Object.keys(tokens.dark).sort()).toEqual(Object.keys(tokens.light).sort());
  });

  it("makes primary a deep navy blue in light mode and a lighter blue in dark mode", () => {
    const light = toHsl(tokens.light.primary);
    expect(light.h).toBeGreaterThanOrEqual(215);
    expect(light.h).toBeLessThanOrEqual(235);
    expect(light.l).toBeLessThan(35);
    expect(light.s).toBeGreaterThan(40);
    const dark = toHsl(tokens.dark.primary);
    expect(dark.h).toBeGreaterThanOrEqual(210);
    expect(dark.h).toBeLessThanOrEqual(235);
  });

  for (const theme of ["light", "dark"] as const) {
    it(`meets WCAG AA for every pair the components use (${theme})`, () => {
      const failures = CONTRAST_PAIRS.map((pair) => ({
        ...pair,
        ratio: contrastRatio(tokens[theme][pair.fg], tokens[theme][pair.bg]),
      }))
        .filter((p) => p.ratio < p.min)
        .map((p) => `${p.fg} on ${p.bg}: ${p.ratio.toFixed(2)} < ${p.min} (${p.use})`);
      expect(failures).toEqual([]);
    });
  }

  it("checks text, badges, agent accents and brand primary on surfaces", () => {
    const uses = CONTRAST_PAIRS.map((p) => `${p.fg}/${p.bg}`);
    expect(uses).toContain("text/surface");
    expect(uses).toContain("success/success-soft");
    expect(uses).toContain("agent-fg/agent-law");
    expect(uses).toContain("primary/surface-raised");
    expect(uses).toContain("primary-fg/primary");
  });

  it("keeps raw colors out of components: no hex, rgb() or hsl() literals outside tokens.css", () => {
    const hex = /(^|[^&\w])#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b/;
    const fn = /\b(?:rgb|rgba|hsl|hsla)\(\s*\d/;
    const offenders = Object.entries(SOURCES)
      .filter(([path]) => path !== "/src/design/tokens.css" && !/\.test\.(ts|tsx)$/.test(path))
      .filter(([, text]) => hex.test(text) || fn.test(text))
      .map(([path]) => path);
    expect(offenders).toEqual([]);
  });

  it("respects prefers-reduced-motion", () => {
    const css = SOURCES["/src/index.css"];
    expect(css).toMatch(/@media \(prefers-reduced-motion: reduce\)/);
    expect(css).toMatch(/animation-duration: 0\.01ms !important/);
    expect(css).toMatch(/transition-duration: 0\.01ms !important/);
  });
});
