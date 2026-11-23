import { AlertTriangle, CalendarClock, CheckCircle2, Info, Lock, Scale, X, XCircle, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/lib/cn";
import { daysUntil, formatDate, pluralize } from "@/lib/format";

import { focusRing } from "../focus";
import { Badge, type BadgeTone } from "./Badge";

// ---------------------------------------------------------------- Banner
export type BannerTone = "info" | "success" | "warning" | "danger";

const BANNER_TONES: Record<BannerTone, { icon: LucideIcon; className: string; iconClass: string }> = {
  info: { icon: Info, className: "border-info/30 bg-info-soft", iconClass: "text-info" },
  success: { icon: CheckCircle2, className: "border-success/30 bg-success-soft", iconClass: "text-success" },
  warning: { icon: AlertTriangle, className: "border-warning/30 bg-warning-soft", iconClass: "text-warning" },
  danger: { icon: XCircle, className: "border-danger/30 bg-danger-soft", iconClass: "text-danger" },
};

export interface BannerProps {
  tone?: BannerTone;
  title?: string;
  children: ReactNode;
  action?: ReactNode;
  onDismiss?: () => void;
  className?: string;
  /** `page`: full-width strip under the header; `inline`: rounded box inside content. */
  variant?: "page" | "inline";
}

/** A message about the whole page or account (email not confirmed, test mode, allowance). */
export function Banner({ tone = "info", title, children, action, onDismiss, className, variant = "inline" }: BannerProps) {
  const t = BANNER_TONES[tone];
  const Icon = t.icon;
  return (
    <div
      role={tone === "danger" ? "alert" : "status"}
      data-banner={tone}
      className={cn(
        "flex items-start gap-3 border text-sm text-text",
        variant === "page" ? "border-x-0 border-t-0 px-4 py-2.5 sm:px-6" : "rounded-md p-3.5",
        t.className,
        className,
      )}
    >
      <Icon size={18} aria-hidden="true" className={cn("mt-0.5 shrink-0", t.iconClass)} />
      <div className="flex min-w-0 flex-1 flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          {title && <span className="font-semibold">{title} </span>}
          <span>{children}</span>
        </div>
        {action && <div className="flex shrink-0 flex-wrap gap-2">{action}</div>}
      </div>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Dismiss"
          className={cn("-m-1 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-text-muted hover:text-text", focusRing)}
        >
          <X size={16} aria-hidden="true" />
        </button>
      )}
    </div>
  );
}

// ---------------------------------------------------------------- TrustNote
export type TrustNoteKind = "security" | "disclaimer" | "info";

const TRUST_ICONS: Record<TrustNoteKind, LucideIcon> = { security: Lock, disclaimer: Scale, info: Info };

/**
 * A quiet trust signal (ADR-0035): the security note under sign-up and payment buttons,
 * the disclaimer at every legal decision.
 */
export function TrustNote({ kind = "info", children, className }: { kind?: TrustNoteKind; children: ReactNode; className?: string }) {
  const Icon = TRUST_ICONS[kind];
  return (
    <p data-trust-note={kind} className={cn("flex items-start gap-2 text-xs leading-5 text-text-muted", className)}>
      <Icon size={14} aria-hidden="true" className="mt-0.5 shrink-0 text-text-subtle" />
      <span>{children}</span>
    </p>
  );
}

// ---------------------------------------------------------------- Countdown
export interface CountdownProps {
  /** ISO date of the deadline. */
  date: string;
  /** "Today" for the calculation (recorded runs fix it). */
  today?: Date;
  label?: string;
  className?: string;
}

/** Days until a date (e.g. the 83(b) deadline), with tone by urgency and the date in text. */
export function Countdown({ date, today, label = "Due", className }: CountdownProps) {
  const days = daysUntil(date, today ?? new Date());
  let tone: BadgeTone = "info";
  let text: string;
  if (days < 0) {
    tone = "danger";
    text = `${pluralize(-days, "day")} overdue`;
  } else if (days === 0) {
    tone = "danger";
    text = "Due today";
  } else {
    tone = days <= 7 ? "warning" : "info";
    text = `${pluralize(days, "day")} left`;
  }
  return (
    <span className={cn("inline-flex flex-wrap items-center gap-2", className)} data-days={days}>
      <Badge tone={tone} icon={CalendarClock}>
        {text}
      </Badge>
      <span className="text-sm text-text-muted">
        {label} {formatDate(date)}
      </span>
    </span>
  );
}
