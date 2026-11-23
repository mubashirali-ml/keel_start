import { AlertCircle, Inbox, RotateCw, type LucideIcon } from "lucide-react";
import type { CSSProperties, ReactNode } from "react";

import { friendlyMessage, isApiError } from "@/api/errors";
import { cn } from "@/lib/cn";

import { Button } from "./Button";

// ---------------------------------------------------------------- EmptyState
export interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: ReactNode;
  action?: ReactNode;
  className?: string;
  compact?: boolean;
}

export function EmptyState({ icon: Icon = Inbox, title, description, action, className, compact }: EmptyStateProps) {
  return (
    <div
      data-state="empty"
      className={cn(
        "flex flex-col items-center justify-center rounded-lg border border-dashed bg-surface text-center",
        compact ? "gap-2 px-4 py-6" : "gap-3 px-6 py-12",
        className,
      )}
    >
      <span className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-primary-soft text-primary">
        <Icon size={22} aria-hidden="true" />
      </span>
      <h3 className="text-base font-semibold text-text">{title}</h3>
      {description && <div className="max-w-md text-sm text-text-muted">{description}</div>}
      {action && <div className="mt-2 flex flex-wrap justify-center gap-2">{action}</div>}
    </div>
  );
}

// ---------------------------------------------------------------- ErrorState
export interface ErrorStateProps {
  /** The thrown value; shown as friendly text only (never raw JSON or a stack trace). */
  error?: unknown;
  title?: string;
  message?: string;
  onRetry?: () => void;
  retrying?: boolean;
  /** Extra recovery actions (Go back, Contact support). */
  actions?: ReactNode;
  className?: string;
  compact?: boolean;
}

export function ErrorState({
  error,
  title = "Something went wrong",
  message,
  onRetry,
  retrying,
  actions,
  className,
  compact,
}: ErrorStateProps) {
  const text = message ?? friendlyMessage(error);
  const requestId = isApiError(error) ? error.requestId : null;
  return (
    <div
      role="alert"
      data-state="error"
      className={cn(
        "flex flex-col items-center justify-center rounded-lg border border-danger/30 bg-surface text-center",
        compact ? "gap-2 px-4 py-6" : "gap-3 px-6 py-12",
        className,
      )}
    >
      <span className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-danger-soft text-danger">
        <AlertCircle size={22} aria-hidden="true" />
      </span>
      <h3 className="text-base font-semibold text-text">{title}</h3>
      <p className="max-w-md text-sm text-text-muted">{text}</p>
      {requestId && <p className="text-xs text-text-subtle">Reference: {requestId}</p>}
      {(onRetry || actions) && (
        <div className="mt-2 flex flex-wrap justify-center gap-2">
          {onRetry && (
            <Button variant="secondary" onClick={onRetry} loading={retrying} leftIcon={<RotateCw size={16} aria-hidden="true" />}>
              Try again
            </Button>
          )}
          {actions}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------- Skeleton
const ROUNDED = { sm: "rounded-sm", md: "rounded-md", lg: "rounded-lg", full: "rounded-full" } as const;

export interface SkeletonProps {
  /** Fixed size so content never shifts when it arrives (ADR-0019). */
  width?: CSSProperties["width"];
  height?: CSSProperties["height"];
  className?: string;
  rounded?: "sm" | "md" | "lg" | "full";
}

export function Skeleton({ width = "100%", height = 16, className, rounded = "md" }: SkeletonProps) {
  return (
    <span
      aria-hidden="true"
      data-skeleton=""
      style={{ width, height }}
      className={cn("block animate-shimmer bg-surface-muted motion-reduce:animate-none", ROUNDED[rounded], className)}
    />
  );
}

/** A labelled loading region made of skeleton lines (screen readers hear "Loading…"). */
export function LoadingBlock({ label = "Loading…", lines = 3, className }: { label?: string; lines?: number; className?: string }) {
  return (
    <div role="status" aria-live="polite" data-state="loading" className={cn("grid gap-3", className)}>
      <span className="sr-only">{label}</span>
      <Skeleton height={28} width="40%" />
      {Array.from({ length: lines }, (_, i) => (
        <Skeleton key={i} height={16} width={i === lines - 1 ? "60%" : "100%"} />
      ))}
    </div>
  );
}
