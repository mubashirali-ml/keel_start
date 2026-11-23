import * as ProgressPrimitive from "@radix-ui/react-progress";

import { cn } from "@/lib/cn";

export interface ProgressProps {
  value: number; // 0-100
  label: string;
  showValue?: boolean;
  size?: "sm" | "md";
  className?: string;
}

export function Progress({ value, label, showValue = false, size = "md", className }: ProgressProps) {
  const clamped = Math.max(0, Math.min(100, Math.round(value)));
  return (
    <div className={cn("grid gap-1.5", className)}>
      {showValue && (
        <div className="flex items-center justify-between text-xs font-medium text-text-muted">
          <span>{label}</span>
          <span>{clamped}%</span>
        </div>
      )}
      <ProgressPrimitive.Root
        value={clamped}
        aria-label={label}
        aria-valuetext={`${clamped}%`}
        className={cn("relative w-full overflow-hidden rounded-full bg-surface-muted", size === "sm" ? "h-1.5" : "h-2.5")}
      >
        <ProgressPrimitive.Indicator
          className="h-full rounded-full bg-primary transition-[width] duration-slow"
          style={{ width: `${clamped}%` }}
        />
      </ProgressPrimitive.Root>
    </div>
  );
}
