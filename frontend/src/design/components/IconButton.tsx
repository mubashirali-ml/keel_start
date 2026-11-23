import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";

import { cn } from "@/lib/cn";

import { focusRing } from "../focus";

export interface IconButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "aria-label" | "children"> {
  /** Required: an icon-only button must say what it does (ADR-0019). */
  "aria-label": string;
  icon: ReactNode;
  variant?: "ghost" | "secondary" | "primary";
  size?: "sm" | "md";
}

const VARIANTS = {
  ghost: "text-text-muted hover:bg-surface-muted hover:text-text",
  secondary: "border border-border-strong/60 bg-surface text-text shadow-sm hover:bg-surface-muted",
  primary: "bg-primary text-primary-fg hover:bg-primary-hover",
};

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(function IconButton(
  { icon, variant = "ghost", size = "md", className, type, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type ?? "button"}
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-md transition-colors duration-fast disabled:pointer-events-none disabled:opacity-55",
        size === "sm" ? "h-8 w-8" : "h-10 w-10",
        VARIANTS[variant],
        focusRing,
        className,
      )}
      {...rest}
    >
      <span aria-hidden="true" className="inline-flex">
        {icon}
      </span>
    </button>
  );
});
