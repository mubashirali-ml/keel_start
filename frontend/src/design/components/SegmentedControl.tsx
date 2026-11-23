import * as RadioPrimitive from "@radix-ui/react-radio-group";
import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

import { focusRingInset } from "../focus";

export interface SegmentedOption<T extends string> {
  value: T;
  label: ReactNode;
}

export interface SegmentedControlProps<T extends string> {
  options: SegmentedOption<T>[];
  value: T;
  onValueChange: (value: T) => void;
  "aria-label": string;
  className?: string;
}

/** A compact one-of-N switch (e.g. Chat / Workspace on phones). Arrow keys move between options. */
export function SegmentedControl<T extends string>({ options, value, onValueChange, className, ...aria }: SegmentedControlProps<T>) {
  return (
    <RadioPrimitive.Root
      aria-label={aria["aria-label"]}
      value={value}
      onValueChange={(v) => onValueChange(v as T)}
      orientation="horizontal"
      className={cn("inline-grid auto-cols-fr grid-flow-col rounded-md border bg-surface-muted p-1", className)}
    >
      {options.map((option) => (
        <RadioPrimitive.Item
          key={option.value}
          value={option.value}
          className={cn(
            "inline-flex h-8 items-center justify-center gap-1.5 rounded-sm px-3 text-sm font-medium text-text-muted transition-colors duration-fast",
            "hover:text-text data-[state=checked]:bg-surface data-[state=checked]:text-text data-[state=checked]:shadow-sm",
            focusRingInset,
          )}
        >
          {option.label}
        </RadioPrimitive.Item>
      ))}
    </RadioPrimitive.Root>
  );
}
