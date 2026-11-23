import * as CheckboxPrimitive from "@radix-ui/react-checkbox";
import { Check, Minus } from "lucide-react";
import { forwardRef, useId, type ReactNode } from "react";

import { cn } from "@/lib/cn";

import { focusRing } from "../focus";

export interface CheckboxProps extends Omit<CheckboxPrimitive.CheckboxProps, "children"> {
  label?: ReactNode;
  description?: ReactNode;
}

export const Checkbox = forwardRef<HTMLButtonElement, CheckboxProps>(function Checkbox(
  { label, description, className, id, ...rest },
  ref,
) {
  const auto = useId();
  const boxId = id ?? auto;
  const descId = description ? `${boxId}-desc` : undefined;
  const box = (
    <CheckboxPrimitive.Root
      ref={ref}
      id={boxId}
      aria-describedby={descId}
      className={cn(
        "peer mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-sm border border-border-strong bg-surface text-primary-fg shadow-sm",
        "transition-colors duration-fast data-[state=checked]:border-primary data-[state=checked]:bg-primary",
        "data-[state=indeterminate]:border-primary data-[state=indeterminate]:bg-primary disabled:cursor-not-allowed disabled:opacity-55",
        focusRing,
        className,
      )}
      {...rest}
    >
      <CheckboxPrimitive.Indicator>
        {rest.checked === "indeterminate" ? (
          <Minus size={14} aria-hidden="true" />
        ) : (
          <Check size={14} strokeWidth={3} aria-hidden="true" />
        )}
      </CheckboxPrimitive.Indicator>
    </CheckboxPrimitive.Root>
  );
  if (!label) return box;
  return (
    <div className="flex items-start gap-3">
      {box}
      <div className="grid gap-0.5">
        <label htmlFor={boxId} className="cursor-pointer text-sm font-medium text-text peer-disabled:cursor-not-allowed">
          {label}
        </label>
        {description && (
          <p id={descId} className="text-sm text-text-muted">
            {description}
          </p>
        )}
      </div>
    </div>
  );
});
