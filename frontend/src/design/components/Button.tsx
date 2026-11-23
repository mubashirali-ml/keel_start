import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";

import { cn } from "@/lib/cn";

import { focusRing } from "../focus";
import { Spinner } from "./Spinner";

export const buttonVariants = cva(
  [
    "inline-flex select-none items-center justify-center gap-2 whitespace-nowrap rounded-md font-medium",
    "transition-colors duration-fast disabled:pointer-events-none disabled:opacity-55",
    focusRing,
  ],
  {
    variants: {
      variant: {
        primary: "bg-primary text-primary-fg shadow-sm hover:bg-primary-hover",
        secondary: "border border-border-strong/60 bg-surface text-text shadow-sm hover:bg-surface-muted",
        ghost: "text-text hover:bg-surface-muted",
        danger: "bg-danger text-danger-fg shadow-sm hover:bg-danger/90",
        link: "h-auto px-0 text-primary underline-offset-4 hover:underline",
      },
      size: {
        sm: "h-8 px-3 text-sm",
        md: "h-10 px-4 text-sm",
        lg: "h-12 px-6 text-base",
      },
    },
    compoundVariants: [{ variant: "link", className: "h-auto px-0" }],
    defaultVariants: { variant: "primary", size: "md" },
  },
);

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  /** Shows a spinner, keeps the width and blocks clicks. */
  loading?: boolean;
  /** Text announced while loading (defaults to the button text). */
  loadingText?: string;
  /** Render the child element (e.g. a router Link) with button styles. */
  asChild?: boolean;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className, variant, size, loading = false, loadingText, asChild = false, leftIcon, rightIcon, children, disabled, type, ...rest },
  ref,
) {
  const classes = cn(buttonVariants({ variant, size }), className);
  if (asChild) {
    return (
      <Slot ref={ref} className={classes} {...rest}>
        {children}
      </Slot>
    );
  }
  return (
    <button
      ref={ref}
      type={type ?? "button"}
      className={classes}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading ? <Spinner size={16} /> : leftIcon}
      <span>{loading && loadingText ? loadingText : children}</span>
      {!loading && rightIcon}
    </button>
  );
});
