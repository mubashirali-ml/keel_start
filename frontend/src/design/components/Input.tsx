import { forwardRef, type InputHTMLAttributes, type TextareaHTMLAttributes } from "react";

import { cn } from "@/lib/cn";

const field =
  "w-full rounded-md border border-border-strong/70 bg-surface text-text shadow-sm placeholder:text-text-subtle " +
  "transition-colors duration-fast hover:border-border-strong disabled:cursor-not-allowed disabled:bg-surface-muted disabled:opacity-70 " +
  "outline-none focus-visible:border-focus-ring focus-visible:ring-2 focus-visible:ring-focus-ring/60 " +
  "aria-[invalid=true]:border-danger aria-[invalid=true]:focus-visible:ring-danger/40";

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  invalid?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input({ className, invalid, ...rest }, ref) {
  return (
    <input
      ref={ref}
      aria-invalid={invalid || rest["aria-invalid"] || undefined}
      className={cn(field, "h-10 px-3 text-base sm:text-sm", className)}
      {...rest}
    />
  );
});

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  invalid?: boolean;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { className, invalid, rows = 4, ...rest },
  ref,
) {
  return (
    <textarea
      ref={ref}
      rows={rows}
      aria-invalid={invalid || rest["aria-invalid"] || undefined}
      className={cn(field, "min-h-[5rem] px-3 py-2 text-base leading-6 sm:text-sm", className)}
      {...rest}
    />
  );
});
