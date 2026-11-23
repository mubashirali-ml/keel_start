import { zodResolver } from "@hookform/resolvers/zod";
import { cloneElement, isValidElement, useId, type ReactElement, type ReactNode } from "react";
import { useForm, type DefaultValues, type FieldValues, type UseFormProps } from "react-hook-form";
import type { ZodType, ZodTypeDef } from "zod";

import { cn } from "@/lib/cn";

import { Label } from "./Label";

export interface FormFieldProps {
  label: ReactNode;
  /** The control: `Input`, `Textarea`, `Select`… It receives id, aria-invalid and aria-describedby. */
  children: ReactElement;
  /** Error text (e.g. `errors.email?.message` from a zod schema). */
  error?: string;
  hint?: ReactNode;
  required?: boolean;
  className?: string;
  id?: string;
}

/**
 * Label + control + hint + error, wired for assistive tech: the label names the control,
 * the hint and error are linked with `aria-describedby`, `aria-invalid` is set, and the
 * error is announced (`role="alert"`) when it appears.
 */
export function FormField({ label, children, error, hint, required, className, id }: FormFieldProps) {
  const auto = useId();
  const childId = isValidElement<{ id?: string }>(children) ? children.props.id : undefined;
  const controlId = id ?? childId ?? auto;
  const hintId = hint ? `${controlId}-hint` : undefined;
  const errorId = error ? `${controlId}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(" ") || undefined;
  const control = cloneElement(children as ReactElement<Record<string, unknown>>, {
    id: controlId,
    "aria-invalid": error ? true : undefined,
    "aria-describedby": describedBy,
    "aria-required": required || undefined,
  });
  return (
    <div className={cn("grid gap-1.5", className)} data-field="">
      <Label htmlFor={controlId}>
        {label}
        {required && (
          <span aria-hidden="true" className="ml-0.5 text-danger">
            *
          </span>
        )}
      </Label>
      {control}
      {hint && (
        <p id={hintId} className="text-sm text-text-muted">
          {hint}
        </p>
      )}
      {error && (
        <p id={errorId} role="alert" className="text-sm font-medium text-danger">
          {error}
        </p>
      )}
    </div>
  );
}

/**
 * `useForm` with a zod schema (ADR-0025): errors appear after a field is touched and on
 * submit; schemas mirror the API's limits.
 */
export function useZodForm<TValues extends FieldValues>(
  schema: ZodType<TValues, ZodTypeDef, unknown>,
  options: Omit<UseFormProps<TValues>, "resolver"> & { defaultValues?: DefaultValues<TValues> } = {},
) {
  return useForm<TValues>({ mode: "onTouched", ...options, resolver: zodResolver(schema) });
}
