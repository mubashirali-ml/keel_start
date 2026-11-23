import * as SwitchPrimitive from "@radix-ui/react-switch";
import { forwardRef, useId, type ReactNode } from "react";

import { cn } from "@/lib/cn";

import { focusRing } from "../focus";

export interface SwitchProps extends Omit<SwitchPrimitive.SwitchProps, "children"> {
  label?: ReactNode;
  description?: ReactNode;
}

export const Switch = forwardRef<HTMLButtonElement, SwitchProps>(function Switch({ label, description, className, id, ...rest }, ref) {
  const auto = useId();
  const switchId = id ?? auto;
  const descId = description ? `${switchId}-desc` : undefined;
  const control = (
    <SwitchPrimitive.Root
      ref={ref}
      id={switchId}
      aria-describedby={descId}
      className={cn(
        "inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent transition-colors duration-fast",
        "bg-border-strong data-[state=checked]:bg-primary disabled:cursor-not-allowed disabled:opacity-55",
        focusRing,
        className,
      )}
      {...rest}
    >
      <SwitchPrimitive.Thumb className="pointer-events-none block h-5 w-5 rounded-full bg-surface shadow-md transition-transform duration-fast data-[state=checked]:translate-x-5 data-[state=unchecked]:translate-x-0" />
    </SwitchPrimitive.Root>
  );
  if (!label) return control;
  return (
    <div className="flex items-start justify-between gap-4">
      <div className="grid gap-0.5">
        <label htmlFor={switchId} className="cursor-pointer text-sm font-medium text-text">
          {label}
        </label>
        {description && (
          <p id={descId} className="text-sm text-text-muted">
            {description}
          </p>
        )}
      </div>
      {control}
    </div>
  );
});
