import * as SelectPrimitive from "@radix-ui/react-select";
import { Check, ChevronDown } from "lucide-react";
import { forwardRef } from "react";

import { cn } from "@/lib/cn";

export interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

export interface SelectProps {
  options: SelectOption[];
  value?: string;
  defaultValue?: string;
  onValueChange?: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  invalid?: boolean;
  id?: string;
  name?: string;
  className?: string;
  "aria-label"?: string;
  "aria-describedby"?: string;
  "aria-invalid"?: boolean;
}

export const Select = forwardRef<HTMLButtonElement, SelectProps>(function Select(
  { options, value, defaultValue, onValueChange, placeholder = "Choose…", disabled, invalid, id, name, className, ...aria },
  ref,
) {
  return (
    <SelectPrimitive.Root value={value} defaultValue={defaultValue} onValueChange={onValueChange} disabled={disabled} name={name}>
      <SelectPrimitive.Trigger
        ref={ref}
        id={id}
        aria-invalid={invalid || aria["aria-invalid"] || undefined}
        aria-label={aria["aria-label"]}
        aria-describedby={aria["aria-describedby"]}
        className={cn(
          "inline-flex h-10 w-full items-center justify-between gap-2 rounded-md border border-border-strong/70 bg-surface px-3 text-left text-base text-text shadow-sm sm:text-sm",
          "transition-colors duration-fast hover:border-border-strong disabled:cursor-not-allowed disabled:opacity-60",
          "outline-none focus-visible:border-focus-ring focus-visible:ring-2 focus-visible:ring-focus-ring/60",
          "aria-[invalid=true]:border-danger data-[placeholder]:text-text-subtle",
          className,
        )}
      >
        <span className="truncate">
          <SelectPrimitive.Value placeholder={placeholder} />
        </span>
        <SelectPrimitive.Icon>
          <ChevronDown size={16} aria-hidden="true" className="text-text-muted" />
        </SelectPrimitive.Icon>
      </SelectPrimitive.Trigger>
      <SelectPrimitive.Portal>
        <SelectPrimitive.Content
          position="popper"
          sideOffset={4}
          className="z-50 max-h-[min(20rem,var(--radix-select-content-available-height))] min-w-[var(--radix-select-trigger-width)] overflow-hidden rounded-md border bg-surface-raised text-text shadow-lg animate-scale-in"
        >
          <SelectPrimitive.Viewport className="p-1">
            {options.map((option) => (
              <SelectPrimitive.Item
                key={option.value}
                value={option.value}
                disabled={option.disabled}
                className="relative flex cursor-pointer select-none items-center rounded-sm py-2 pl-8 pr-3 text-sm outline-none data-[disabled]:pointer-events-none data-[highlighted]:bg-primary-soft data-[disabled]:opacity-50"
              >
                <SelectPrimitive.ItemIndicator className="absolute left-2 inline-flex">
                  <Check size={16} aria-hidden="true" className="text-primary" />
                </SelectPrimitive.ItemIndicator>
                <SelectPrimitive.ItemText>{option.label}</SelectPrimitive.ItemText>
              </SelectPrimitive.Item>
            ))}
          </SelectPrimitive.Viewport>
        </SelectPrimitive.Content>
      </SelectPrimitive.Portal>
    </SelectPrimitive.Root>
  );
});
