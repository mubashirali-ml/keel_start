/**
 * Markdown (`prose`) uses tokens only, in both themes (ADR-0019, T-011 AC2).
 * Runs the real tailwind.config.ts through Tailwind and checks the generated `--tw-prose-*` variables:
 * each must be a valid token color (no `<alpha-value>` left behind, no plugin hex palette).
 */
import postcss from "postcss";
import tailwindcss from "tailwindcss";

import markdownSource from "./components/Markdown.tsx?raw";
import { parseTokens } from "./contrast";
import tokensCss from "./tokens.css?raw";

const tokens = parseTokens(tokensCss);
const TOKEN_COLOR = /^rgb\(var\(--color-([a-z-]+)\)(?: \/ \d+%)?\)$/;
const ROLES = [
  "body",
  "headings",
  "lead",
  "links",
  "bold",
  "counters",
  "bullets",
  "hr",
  "quotes",
  "quote-borders",
  "captions",
  "kbd",
  "kbd-shadows",
  "code",
  "pre-code",
  "pre-bg",
  "th-borders",
  "td-borders",
];

async function generatedProse() {
  // The config's content globs are relative to the frontend folder (vitest's working directory).
  const result = await postcss([tailwindcss({ config: "tailwind.config.ts" })]).process("@tailwind components;", { from: undefined });
  const variables: Record<string, string> = {};
  const colorDecls: string[] = [];
  result.root.walkRules((rule) => {
    if (!rule.selector.includes("prose")) return;
    rule.walkDecls((decl) => {
      if (decl.prop.startsWith("--tw-prose-") && rule.selector === ".prose") variables[decl.prop] = decl.value;
      colorDecls.push(`${rule.selector} { ${decl.prop}: ${decl.value} }`);
    });
  });
  return { css: result.css, variables, colorDecls };
}

describe("Markdown prose colors are tokens (ADR-0019)", () => {
  it("generates every --tw-prose-* variable (and its invert twin) as a plain token color", async () => {
    const { variables } = await generatedProse();
    const bad: string[] = [];
    for (const role of ROLES) {
      for (const prop of [`--tw-prose-${role}`, `--tw-prose-invert-${role}`]) {
        const value = variables[prop];
        const match = value ? TOKEN_COLOR.exec(value) : null;
        if (!match) bad.push(`${prop}: ${value ?? "(missing)"}`);
        else if (!tokens.light[match[1]] || !tokens.dark[match[1]]) bad.push(`${prop}: unknown token ${match[1]}`);
      }
    }
    expect(bad).toEqual([]);
    expect(variables["--tw-prose-links"]).toBe("rgb(var(--color-primary))");
    expect(variables["--tw-prose-pre-bg"]).toBe("rgb(var(--color-surface-muted))");
  });

  it("leaves no <alpha-value> placeholder and no raw colors in the prose styles", async () => {
    const { css, colorDecls } = await generatedProse();
    expect(css).not.toContain("<alpha-value>");
    const raw = /#[0-9a-fA-F]{3,8}\b|\b(?:rgb|rgba|hsl|hsla)\(\s*\d/;
    expect(colorDecls.filter((d) => raw.test(d))).toEqual([]);
  });

  it("does not switch to the plugin's palette in dark mode (no prose-invert: the tokens switch with .dark)", () => {
    expect(markdownSource).not.toContain("prose-invert");
  });
});
