import typography from "@tailwindcss/typography";
import type { Config } from "tailwindcss";

/** A color bound to a token of src/design/tokens.css (ADR-0019). */
const token = (name: string) => `rgb(var(--color-${name}) / <alpha-value>)`;

/**
 * A plain token color for CSS variables. No `<alpha-value>`: Tailwind fills that placeholder only in
 * color utilities, so it would leave an invalid color in the typography plugin's `--tw-prose-*` variables.
 */
const tokenColor = (name: string, alpha?: string) =>
  alpha ? `rgb(var(--color-${name}) / ${alpha})` : `rgb(var(--color-${name}))`;

/**
 * Markdown (`prose`) colors, all tokens; they switch with `.dark` like every other token, so no
 * `prose-invert` is needed. The `invert` set gets the same tokens so a stray `prose-invert` can never
 * bring back the plugin's own gray palette.
 */
const proseRoles: Record<string, [token: string, alpha?: string]> = {
  body: ["text"],
  headings: ["text"],
  lead: ["text-muted"],
  links: ["primary"],
  bold: ["text"],
  counters: ["text-muted"],
  bullets: ["border-strong"],
  hr: ["border"],
  quotes: ["text"],
  "quote-borders": ["border"],
  captions: ["text-muted"],
  kbd: ["text"],
  "kbd-shadows": ["text", "10%"],
  code: ["text"],
  "pre-code": ["text"],
  "pre-bg": ["surface-muted"],
  "th-borders": ["border-strong"],
  "td-borders": ["border"],
};
const proseColors = Object.fromEntries(
  Object.entries(proseRoles).flatMap(([role, [name, alpha]]) => [
    [`--tw-prose-${role}`, tokenColor(name, alpha)],
    [`--tw-prose-invert-${role}`, tokenColor(name, alpha)],
  ]),
);

const tone = (name: string) => ({ DEFAULT: token(name), fg: token(`${name}-fg`), soft: token(`${name}-soft`) });

// `theme.colors` is replaced, not extended: only tokens exist, so no component can use a raw palette color.
const colors = {
  transparent: "transparent",
  current: "currentColor",
  inherit: "inherit",
  bg: token("bg"),
  surface: { DEFAULT: token("surface"), raised: token("surface-raised"), muted: token("surface-muted") },
  border: { DEFAULT: token("border"), strong: token("border-strong") },
  text: { DEFAULT: token("text"), muted: token("text-muted"), subtle: token("text-subtle") },
  primary: {
    DEFAULT: token("primary"),
    hover: token("primary-hover"),
    fg: token("primary-fg"),
    soft: token("primary-soft"),
  },
  success: tone("success"),
  warning: tone("warning"),
  danger: tone("danger"),
  info: tone("info"),
  "focus-ring": token("focus-ring"),
  agent: {
    manager: token("agent-manager"),
    law: token("agent-law"),
    name: token("agent-name"),
    website: token("agent-website"),
    qa: token("agent-qa"),
    guide: token("agent-guide"),
    "cap-table": token("agent-cap-table"),
    signoff: token("agent-signoff"),
    fg: token("agent-fg"),
  },
};

export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    colors,
    fontFamily: {
      sans: ['"Inter Variable"', "Inter", "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
      heading: ['"Inter Variable"', "Inter", "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
      mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
    },
    borderRadius: {
      none: "0",
      sm: "6px",
      DEFAULT: "6px",
      md: "10px",
      lg: "14px",
      xl: "20px",
      full: "9999px",
    },
    boxShadow: {
      none: "none",
      sm: "var(--shadow-sm)",
      DEFAULT: "var(--shadow-sm)",
      md: "var(--shadow-md)",
      lg: "var(--shadow-lg)",
    },
    extend: {
      borderColor: { DEFAULT: token("border") },
      ringColor: { DEFAULT: token("focus-ring") },
      ringOffsetColor: { DEFAULT: token("bg") },
      transitionDuration: { DEFAULT: "150ms", fast: "150ms", slow: "250ms" },
      keyframes: {
        "fade-in": { from: { opacity: "0" }, to: { opacity: "1" } },
        "scale-in": { from: { opacity: "0", transform: "scale(0.97)" }, to: { opacity: "1", transform: "scale(1)" } },
        "slide-in": { from: { opacity: "0", transform: "translateY(8px)" }, to: { opacity: "1", transform: "translateY(0)" } },
        shimmer: { "0%": { opacity: "1" }, "50%": { opacity: "0.55" }, "100%": { opacity: "1" } },
      },
      animation: {
        "fade-in": "fade-in 150ms ease-out",
        "scale-in": "scale-in 150ms ease-out",
        "slide-in": "slide-in 250ms ease-out",
        shimmer: "shimmer 1.6s ease-in-out infinite",
      },
      typography: {
        DEFAULT: {
          css: proseColors,
        },
      },
    },
  },
  plugins: [typography],
} satisfies Config;
