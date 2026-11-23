import { useEffect, useState } from "react";

function matches(query: string): boolean {
  return typeof window !== "undefined" && typeof window.matchMedia === "function" && window.matchMedia(query).matches;
}

/** Live result of a CSS media query; read synchronously on first render (no layout shift). */
export function useMediaQuery(query: string): boolean {
  const [value, setValue] = useState(() => matches(query));
  useEffect(() => {
    if (typeof window.matchMedia !== "function") return;
    const mql = window.matchMedia(query);
    const onChange = () => setValue(mql.matches);
    onChange();
    mql.addEventListener?.("change", onChange);
    return () => mql.removeEventListener?.("change", onChange);
  }, [query]);
  return value;
}

export const QUERIES = {
  /** Below Tailwind's `sm` (640px): tables stack into cards. */
  belowSm: "(max-width: 639.98px)",
  /** Below `lg` (1024px): chat and workspace switch with a segmented control. */
  belowLg: "(max-width: 1023.98px)",
  reducedMotion: "(prefers-reduced-motion: reduce)",
  prefersDark: "(prefers-color-scheme: dark)",
} as const;
