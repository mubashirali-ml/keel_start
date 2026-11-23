/** WCAG 2.x contrast helpers over the token file (used by the token tests and the gallery). */

export type Rgb = [number, number, number];
export type ThemeTokens = Record<string, Rgb>;

/** Parses `--color-*: R G B;` declarations of the `:root, .light` (light) and `.dark` blocks. */
export function parseTokens(css: string): { light: ThemeTokens; dark: ThemeTokens } {
  const block = (selector: RegExp): ThemeTokens => {
    const match = selector.exec(css);
    if (!match) throw new Error(`no ${selector} block in tokens.css`);
    const start = match.index;
    const end = css.indexOf("\n}", start);
    const body = css.slice(start, end);
    const tokens: ThemeTokens = {};
    for (const match of body.matchAll(/--color-([a-z0-9-]+):\s*(\d+)\s+(\d+)\s+(\d+)\s*;/g)) {
      tokens[match[1]] = [Number(match[2]), Number(match[3]), Number(match[4])];
    }
    return tokens;
  };
  return { light: block(/^:root[^{]*\{/m), dark: block(/^\.dark\s*\{/m) };
}

function channel(value: number): number {
  const c = value / 255;
  return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
}

export function luminance([r, g, b]: Rgb): number {
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
}

export function contrastRatio(a: Rgb, b: Rgb): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

/** Hue (0-360), saturation and lightness (0-100) of a color. */
export function toHsl([r, g, b]: Rgb): { h: number; s: number; l: number } {
  const [rn, gn, bn] = [r / 255, g / 255, b / 255];
  const max = Math.max(rn, gn, bn);
  const min = Math.min(rn, gn, bn);
  const l = (max + min) / 2;
  const d = max - min;
  if (d === 0) return { h: 0, s: 0, l: l * 100 };
  const s = d / (1 - Math.abs(2 * l - 1));
  let h: number;
  if (max === rn) h = ((gn - bn) / d) % 6;
  else if (max === gn) h = (bn - rn) / d + 2;
  else h = (rn - gn) / d + 4;
  h = (h * 60 + 360) % 360;
  return { h, s: s * 100, l: l * 100 };
}

const SURFACES = ["bg", "surface", "surface-raised", "surface-muted"] as const;
const TONES = ["success", "warning", "danger", "info"] as const;
export const AGENT_ACCENTS = [
  "agent-manager",
  "agent-law",
  "agent-name",
  "agent-website",
  "agent-qa",
  "agent-guide",
  "agent-cap-table",
  "agent-signoff",
] as const;

export interface ContrastPair {
  fg: string;
  bg: string;
  min: number; // 4.5 text, 3 large text / icons / borders
  use: string;
}

/** Every foreground/background pair the design system uses. */
export const CONTRAST_PAIRS: ContrastPair[] = [
  ...SURFACES.flatMap((bg) => [
    { fg: "text", bg, min: 4.5, use: "body text" },
    { fg: "text-muted", bg, min: 4.5, use: "secondary text" },
    { fg: "text-subtle", bg, min: 4.5, use: "hints and placeholders" },
    { fg: "primary", bg, min: 4.5, use: "brand primary: links, logo, selected tab" },
    { fg: "border-strong", bg, min: 3, use: "input borders" },
    { fg: "focus-ring", bg, min: 3, use: "focus ring" },
    ...TONES.map((tone) => ({ fg: tone, bg, min: 4.5, use: `${tone} text and icons` })),
    ...AGENT_ACCENTS.map((agent) => ({ fg: agent, bg, min: 4.5, use: `${agent} name label` })),
  ]),
  { fg: "primary-fg", bg: "primary", min: 4.5, use: "primary button" },
  { fg: "primary-fg", bg: "primary-hover", min: 4.5, use: "primary button hover" },
  { fg: "primary", bg: "primary-soft", min: 4.5, use: "selected item" },
  { fg: "text", bg: "primary-soft", min: 4.5, use: "selected item text" },
  ...TONES.flatMap((tone) => [
    { fg: `${tone}-fg`, bg: tone, min: 4.5, use: `solid ${tone} badge / button` },
    { fg: tone, bg: `${tone}-soft`, min: 4.5, use: `${tone} badge` },
    { fg: "text", bg: `${tone}-soft`, min: 4.5, use: `${tone} banner text` },
  ]),
  ...AGENT_ACCENTS.map((agent) => ({ fg: "agent-fg", bg: agent, min: 4.5, use: `${agent} avatar icon` })),
];
