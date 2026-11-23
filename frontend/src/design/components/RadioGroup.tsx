import * as RadioPrimitive from "@radix-ui/react-radio-group";
import { forwardRef, useId, type ReactNode } from "react";

import { cn } from "@/lib/cn";

import { focusRing } from "../focus";

export interface RadioOption {
  value: string;
  label: ReactNode;
  description?: ReactNode;
  disabled?: boolean;
}

export interface RadioGroupProps extends Omit<RadioPrimitive.RadioGroupProps, "children"> {
  options: RadioOption[];
  /** `list`: stacked radios; `cards`: selectable cards (e.g. the monthly / yearly plan choice). */
  layout?: "list" | "cards";
}

export const RadioGroup = forwardRef<HTMLDivElement, RadioGroupProps>(function RadioGroup(
  { options, layout = "list", className, value, defaultValue, ...rest },
  ref,
) {
  const base = useId();
  return (
    <RadioPrimitive.Root
      ref={ref}
      value={value}
      defaultValue={defaultValue}
      className={cn(layout === "cards" ? "grid gap-3 sm:grid-cols-2" : "grid gap-3", className)}
      {...rest}
    >
      {options.map((option, i) => {
        const id = `${base}-${i}`;
        const descId = option.description ? `${id}-desc` : undefined;
        return (
          <div
            key={option.value}
            className={cn(
              "flex items-start gap-3",
              layout === "cards" &&
                "relative rounded-md border bg-surface p-4 transition-colors duration-fast has-[[data-state=checked]]:border-primary has-[[data-state=checked]]:bg-primary-soft",
            )}
          >
            <RadioPrimitive.Item
              id={id}
              value={option.value}
              disabled={option.disabled}
              aria-describedby={descId}
              className={cn(
                "relative z-10 mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-border-strong bg-surface",
                "data-[state=checked]:border-primary disabled:cursor-not-allowed disabled:opacity-55",
                focusRing,
              )}
            >
              <RadioPrimitive.Indicator className="h-2.5 w-2.5 rounded-full bg-primary" />
            </RadioPrimitive.Item>
            <div className="grid gap-0.5">
              <label
                htmlFor={id}
                className={cn("cursor-pointer text-sm font-medium text-text", layout === "cards" && "after:absolute after:inset-0")}
              >
                {option.label}
              </label>
              {option.description && (
                <p id={descId} className="text-sm text-text-muted">
                  {option.description}
                </p>
              )}
            </div>
          </div>
        );
      })}
    </RadioPrimitive.Root>
  );
});
