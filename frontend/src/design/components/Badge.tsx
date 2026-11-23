import { AlertTriangle, CheckCircle2, Circle, Info, Sparkles, XCircle, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

export type BadgeTone = "neutral" | "success" | "warning" | "danger" | "info" | "primary";

const TONES: Record<BadgeTone, { className: string; icon: LucideIcon }> = {
  neutral: { className: "border-border bg-surface-muted text-text-muted", icon: Circle },
  success: { className: "border-success/25 bg-success-soft text-success", icon: CheckCircle2 },
  warning: { className: "border-warning/25 bg-warning-soft text-warning", icon: AlertTriangle },
  danger: { className: "border-danger/25 bg-danger-soft text-danger", icon: XCircle },
  info: { className: "border-info/25 bg-info-soft text-info", icon: Info },
  primary: { className: "border-primary/25 bg-primary-soft text-primary", icon: Sparkles },
};

export interface BadgeProps {
  tone?: BadgeTone;
  /** Override the tone's icon. Badges always pair an icon with text, never colour alone (ADR-0019). */
  icon?: LucideIcon;
  children: ReactNode;
  className?: string;
  size?: "sm" | "md";
}

export function Badge({ tone = "neutral", icon, children, className, size = "md" }: BadgeProps) {
  const t = TONES[tone];
  const Icon = icon ?? t.icon;
  return (
    <span
      data-tone={tone}
      className={cn(
        "inline-flex max-w-full items-center gap-1 whitespace-nowrap rounded-full border font-medium",
        size === "sm" ? "px-2 py-0.5 text-xs" : "px-2.5 py-0.5 text-xs leading-5",
        t.className,
        className,
      )}
    >
      <Icon size={size === "sm" ? 12 : 14} aria-hidden="true" className="shrink-0" />
      <span className="truncate">{children}</span>
    </span>
  );
}
