import { forwardRef, type HTMLAttributes } from "react";

import { cn } from "@/lib/cn";

export const Card = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement> & { raised?: boolean }>(function Card(
  { className, raised = false, ...rest },
  ref,
) {
  return (
    <div
      ref={ref}
      className={cn("rounded-lg border bg-surface text-text", raised ? "shadow-md" : "shadow-sm", className)}
      {...rest}
    />
  );
});

export function CardHeader({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex flex-col gap-1 p-5 pb-3", className)} {...rest} />;
}

export function CardTitle({ className, as: Tag = "h3", ...rest }: HTMLAttributes<HTMLHeadingElement> & { as?: "h2" | "h3" | "h4" }) {
  return <Tag className={cn("text-lg font-semibold leading-7 text-text", className)} {...rest} />;
}

export function CardDescription({ className, ...rest }: HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn("text-sm text-text-muted", className)} {...rest} />;
}

export function CardContent({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("p-5 pt-0", className)} {...rest} />;
}

export function CardFooter({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex flex-wrap items-center gap-3 border-t px-5 py-4", className)} {...rest} />;
}
