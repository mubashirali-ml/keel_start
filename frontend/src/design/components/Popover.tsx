import * as PopoverPrimitive from "@radix-ui/react-popover";
import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

export const Popover = PopoverPrimitive.Root;
export const PopoverTrigger = PopoverPrimitive.Trigger;
export const PopoverClose = PopoverPrimitive.Close;

export interface PopoverContentProps {
  children: ReactNode;
  align?: "start" | "center" | "end";
  side?: "top" | "right" | "bottom" | "left";
  className?: string;
  "aria-label"?: string;
}

/** Floating panel (help popovers, small forms). Escape and outside click close it. */
export function PopoverContent({ children, align = "center", side = "bottom", className, ...aria }: PopoverContentProps) {
  return (
    <PopoverPrimitive.Portal>
      <PopoverPrimitive.Content
        align={align}
        side={side}
        sideOffset={8}
        collisionPadding={12}
        aria-label={aria["aria-label"]}
        className={cn(
          "z-50 w-72 max-w-[calc(100vw-1.5rem)] rounded-md border bg-surface-raised p-4 text-sm text-text shadow-lg outline-none animate-scale-in",
          className,
        )}
      >
        {children}
      </PopoverPrimitive.Content>
    </PopoverPrimitive.Portal>
  );
}
