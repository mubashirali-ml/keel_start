/** Formatting helpers (dates, percents, shares, money). Decimals arrive from the API as strings. */

const LOCALE = "en-US";

function toDate(value: string | Date): Date {
  if (value instanceof Date) return value;
  // A bare ISO date ("2026-12-01") is a calendar day, not midnight UTC: parse it as local.
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (m) return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  return new Date(value);
}

/** "Dec 1, 2026" */
export function formatDate(value: string | Date | null | undefined): string {
  if (!value) return "";
  return toDate(value).toLocaleDateString(LOCALE, { year: "numeric", month: "short", day: "numeric" });
}

/** "Dec 1, 2026, 9:30 AM" */
export function formatDateTime(value: string | Date | null | undefined): string {
  if (!value) return "";
  return toDate(value).toLocaleString(LOCALE, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

/** "60%", "33.33%" from a decimal string or number; trailing zeros dropped. */
export function formatPercent(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "";
  const n = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(n)) return String(value);
  return `${n.toLocaleString(LOCALE, { maximumFractionDigits: 2 })}%`;
}

/** "6,000,000" */
export function formatShares(value: number | null | undefined): string {
  if (value === null || value === undefined) return "";
  return value.toLocaleString(LOCALE);
}

/** "$29" or "$29.50" from cents. */
export function formatCents(cents: number): string {
  const dollars = cents / 100;
  return dollars.toLocaleString(LOCALE, {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: Number.isInteger(dollars) ? 0 : 2,
    maximumFractionDigits: 2,
  });
}

/** Whole calendar days from `today` until `date` (negative when past). */
export function daysUntil(date: string | Date, today: Date = new Date()): number {
  const a = toDate(date);
  const start = Date.UTC(today.getFullYear(), today.getMonth(), today.getDate());
  const end = Date.UTC(a.getFullYear(), a.getMonth(), a.getDate());
  return Math.round((end - start) / 86_400_000);
}

/** "1 company", "3 companies" */
export function pluralize(count: number, singular: string, plural = `${singular}s`): string {
  return `${count.toLocaleString(LOCALE)} ${count === 1 ? singular : plural}`;
}
