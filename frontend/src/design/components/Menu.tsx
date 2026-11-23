import * as MenuPrimitive from "@radix-ui/react-dropdown-menu";
import { forwardRef, type ComponentPropsWithoutRef, type ElementRef, type ReactNode } from "react";

import { cn } from "@/lib/cn";

/** Dropdown menu (Radix): arrow keys, typeahead, Escape; used by the header menus. */
export const Menu = MenuPrimitive.Root;
export const MenuTrigger = MenuPrimitive.Trigger;
export const MenuGroup = MenuPrimitive.Group;

export function MenuContent({
  children,
  align = "end",
  className,
  ...rest
}: { children: ReactNode; align?: "start" | "center" | "end"; className?: string } & Omit<
  ComponentPropsWithoutRef<typeof MenuPrimitive.Content>,
  "children" | "align"
>) {
  return (
    <MenuPrimitive.Portal>
      <MenuPrimitive.Content
        align={align}
        sideOffset={8}
        collisionPadding={12}
        className={cn(
          "z-50 min-w-[14rem] max-w-[calc(100vw-1.5rem)] overflow-hidden rounded-md border bg-surface-raised p-1 text-sm text-text shadow-lg animate-scale-in",
          className,
        )}
        {...rest}
      >
        {children}
      </MenuPrimitive.Content>
    </MenuPrimitive.Portal>
  );
}

export const MenuItem = forwardRef<
  ElementRef<typeof MenuPrimitive.Item>,
  ComponentPropsWithoutRef<typeof MenuPrimitive.Item> & { icon?: ReactNode; danger?: boolean }
>(function MenuItem({ className, icon, danger, children, ...rest }, ref) {
  return (
    <MenuPrimitive.Item
      ref={ref}
      className={cn(
        "flex cursor-pointer select-none items-center gap-2.5 rounded-sm px-2.5 py-2 outline-none",
        "data-[highlighted]:bg-primary-soft data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
        danger ? "text-danger" : "text-text",
        className,
      )}
      {...rest}
    >
      {icon && (
        <span aria-hidden="true" className="inline-flex text-text-muted">
          {icon}
        </span>
      )}
      {children}
    </MenuPrimitive.Item>
  );
});

export function MenuLabel({ children, className }: { children: ReactNode; className?: string }) {
  return <MenuPrimitive.Label className={cn("px-2.5 py-2 text-xs text-text-muted", className)}>{children}</MenuPrimitive.Label>;
}

export function MenuSeparator() {
  return <MenuPrimitive.Separator className="my-1 h-px bg-border" />;
}
