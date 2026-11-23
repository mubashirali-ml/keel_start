import * as TabsPrimitive from "@radix-ui/react-tabs";
import { forwardRef, type ComponentPropsWithoutRef, type ElementRef } from "react";

import { cn } from "@/lib/cn";

import { focusRingInset } from "../focus";

/** Tabs (Radix): arrow keys move between tabs, Home/End jump, the selected tab is in the tab order. */
export const Tabs = TabsPrimitive.Root;

export const TabsList = forwardRef<
  ElementRef<typeof TabsPrimitive.List>,
  ComponentPropsWithoutRef<typeof TabsPrimitive.List> & { scrollable?: boolean }
>(function TabsList({ className, scrollable = false, ...rest }, ref) {
  return (
    <TabsPrimitive.List
      ref={ref}
      className={cn(
        "flex items-stretch gap-1 border-b",
        // On narrow screens only the tab list scrolls sideways, never the page (ADR-0019).
        scrollable && "overflow-x-auto overscroll-x-contain [scrollbar-width:thin]",
        className,
      )}
      {...rest}
    />
  );
});

export const TabsTrigger = forwardRef<
  ElementRef<typeof TabsPrimitive.Trigger>,
  ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>
>(function TabsTrigger({ className, ...rest }, ref) {
  return (
    <TabsPrimitive.Trigger
      ref={ref}
      className={cn(
        "relative -mb-px inline-flex shrink-0 items-center gap-2 whitespace-nowrap rounded-t-sm border-b-2 border-transparent px-3 py-2.5 text-sm font-medium text-text-muted",
        "transition-colors duration-fast hover:text-text disabled:pointer-events-none disabled:opacity-50",
        "data-[state=active]:border-primary data-[state=active]:text-primary",
        focusRingInset,
        className,
      )}
      {...rest}
    />
  );
});

export const TabsContent = forwardRef<
  ElementRef<typeof TabsPrimitive.Content>,
  ComponentPropsWithoutRef<typeof TabsPrimitive.Content>
>(function TabsContent({ className, ...rest }, ref) {
  return <TabsPrimitive.Content ref={ref} className={cn("pt-4 outline-none focus-visible:ring-2 focus-visible:ring-focus-ring", className)} {...rest} />;
});
