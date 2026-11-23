import type { SVGProps } from "react";

/**
 * The Keel mark (ADR-0041): a sailboat seen side-on. A triangular sail above a shallow hull,
 * with a short keel fin under the hull's centre. Flat shapes in `currentColor`, so the
 * caller picks the colour (`text-primary` for the brand colour, or inherit for one colour).
 * Drawn on a 32 x 32 grid so it stays crisp at 16 px (favicon) and 32 px.
 */
export const MARK_PATHS = {
  sail: "M13 2.5C18.5 7 22.5 12.5 25.5 19.5H13Z",
  hull: "M3 21.5H29L25 27H7Z",
  keel: "M14.25 27H17.75L17 30.5H15Z",
} as const;

export interface LogoMarkProps extends Omit<SVGProps<SVGSVGElement>, "children"> {
  size?: number;
  /** Accessible name; when omitted the mark is decorative (aria-hidden). */
  title?: string;
}

export function LogoMark({ size = 28, title, ...rest }: LogoMarkProps) {
  const a11y = title ? { role: "img", "aria-label": title } : { "aria-hidden": true as const };
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="currentColor"
      xmlns="http://www.w3.org/2000/svg"
      focusable="false"
      data-logo-mark=""
      {...a11y}
      {...rest}
    >
      <path d={MARK_PATHS.sail} />
      <path d={MARK_PATHS.hull} />
      <path d={MARK_PATHS.keel} />
    </svg>
  );
}
