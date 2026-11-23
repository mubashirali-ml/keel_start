/**
 * The brand (ADR-0041). This folder is the only place in src/ that spells out the product
 * name: everything else reads `PublicConfig.brand_name` (via `useBrandName`) or these
 * helpers. Renaming = BRAND_NAME on the backend, this fallback, and the logo artwork.
 *
 * Plain TypeScript with no imports: vite.config.ts also reads it to fill index.html.
 */

/** Compiled fallback used until `GET /api/config` answers (or while it doesn't exist yet). */
export const BRAND_FALLBACK_NAME = "Keelstart";

/** Tagline: one constant (default pending Q-010). */
export const TAGLINE = "Launch your company with a team of AI agents";

/** Placeholder the owner fills before launch (ADR-0041 footer). */
export const COMPANY_LEGAL_NAME = "[COMPANY LEGAL NAME]";

/** "Not legal advice. Keelstart is not a law firm." */
export function disclaimerLine(brand: string = BRAND_FALLBACK_NAME): string {
  return `Not legal advice. ${brand} is not a law firm.`;
}

/** Every page title: `{Page} · Keelstart`. */
export function pageTitle(page: string, brand: string = BRAND_FALLBACK_NAME): string {
  return `${page} · ${brand}`;
}

/** The landing page title: `Keelstart · Launch your company with a team of AI agents`. */
export function landingTitle(brand: string = BRAND_FALLBACK_NAME): string {
  return `${brand} · ${TAGLINE}`;
}

/** Footer line: "© {year} [COMPANY LEGAL NAME]. Keelstart is a product of [COMPANY LEGAL NAME]." */
export function footerLine(year: number, brand: string = BRAND_FALLBACK_NAME): string {
  return `© ${year} ${COMPANY_LEGAL_NAME}. ${brand} is a product of ${COMPANY_LEGAL_NAME}.`;
}

/** File-name slug of the brand, e.g. for downloads ("keelstart"). */
export function brandSlug(brand: string = BRAND_FALLBACK_NAME): string {
  return brand
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}
