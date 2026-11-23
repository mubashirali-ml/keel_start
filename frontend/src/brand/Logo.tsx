import { cn } from "@/lib/cn";

import { useBrandName } from "./BrandName";
import { LogoMark } from "./LogoMark";

const SIZES = {
  sm: { mark: 22, text: "text-base" },
  md: { mark: 28, text: "text-lg" },
  lg: { mark: 40, text: "text-2xl" },
  xl: { mark: 56, text: "text-3xl" },
} as const;

export interface LogoProps {
  size?: keyof typeof SIZES;
  /** `brand`: mark in primary, word mark in text colour. `current`: one colour (currentColor). */
  tone?: "brand" | "current";
  /** Hide the word mark entirely (the accessible name stays). */
  markOnly?: boolean;
  /** Classes for the word mark, e.g. "hidden sm:inline" for an icon-only header on phones. */
  wordmarkClassName?: string;
  className?: string;
}

/** The sailboat mark with the word mark to its right, in the heading font (ADR-0041). */
export function Logo({ size = "md", tone = "brand", markOnly = false, className, wordmarkClassName }: LogoProps) {
  const brand = useBrandName();
  const s = SIZES[size];
  return (
    <span
      role="img"
      aria-label={brand}
      data-logo=""
      className={cn("inline-flex items-center gap-2 leading-none", tone === "brand" ? "text-text" : "text-current", className)}
    >
      <LogoMark size={s.mark} className={cn("shrink-0", tone === "brand" && "text-primary")} />
      {!markOnly && (
        <span aria-hidden="true" className={cn("font-heading font-semibold tracking-tight", s.text, wordmarkClassName)}>
          {brand}
        </span>
      )}
    </span>
  );
}
