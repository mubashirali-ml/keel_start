import * as ToastPrimitive from "@radix-ui/react-toast";
import { AlertTriangle, CheckCircle2, Info, X, XCircle, type LucideIcon } from "lucide-react";
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

import { cn } from "@/lib/cn";

import { focusRing } from "../focus";

export type ToastTone = "info" | "success" | "warning" | "danger";

export interface ToastOptions {
  title: string;
  description?: string;
  tone?: ToastTone;
  /** Milliseconds before it closes on its own (default 5 s; paused on hover/focus). */
  duration?: number;
  action?: { label: string; onClick: () => void };
}

interface ToastItem extends ToastOptions {
  id: number;
  open: boolean;
}

interface ToastApi {
  toast: (options: ToastOptions) => number;
  dismiss: (id: number) => void;
}

const ToastContext = createContext<ToastApi | null>(null);

const TONES: Record<ToastTone, { icon: LucideIcon; className: string }> = {
  info: { icon: Info, className: "text-info" },
  success: { icon: CheckCircle2, className: "text-success" },
  warning: { icon: AlertTriangle, className: "text-warning" },
  danger: { icon: XCircle, className: "text-danger" },
};

let nextId = 1;

/**
 * Toasts (Radix): announced politely to screen readers, F8 jumps to them, they pause on
 * hover/focus and can be swiped or closed. Wrap the app once; call `useToast().toast(...)`.
 */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);

  const dismiss = useCallback((id: number) => {
    setItems((all) => all.map((t) => (t.id === id ? { ...t, open: false } : t)));
    window.setTimeout(() => setItems((all) => all.filter((t) => t.id !== id)), 300);
  }, []);

  const toast = useCallback((options: ToastOptions) => {
    const id = nextId++;
    setItems((all) => [...all.slice(-3), { ...options, id, open: true }]);
    return id;
  }, []);

  const api = useMemo(() => ({ toast, dismiss }), [toast, dismiss]);

  return (
    <ToastContext.Provider value={api}>
      <ToastPrimitive.Provider swipeDirection="right" label="Notification">
        {children}
        {items.map((item) => {
          const tone = TONES[item.tone ?? "info"];
          const Icon = tone.icon;
          return (
            <ToastPrimitive.Root
              key={item.id}
              type="background"
              open={item.open}
              duration={item.duration ?? 5000}
              onOpenChange={(open) => !open && dismiss(item.id)}
              className={cn(
                "group pointer-events-auto relative flex w-full items-start gap-3 rounded-md border bg-surface-raised p-4 pr-10 text-text shadow-lg",
                "data-[state=open]:animate-slide-in data-[state=closed]:animate-fade-in data-[state=closed]:opacity-0",
                "data-[swipe=move]:translate-x-[var(--radix-toast-swipe-move-x)] data-[swipe=end]:translate-x-[var(--radix-toast-swipe-end-x)]",
                focusRing,
              )}
            >
              <Icon size={20} aria-hidden="true" className={cn("mt-0.5 shrink-0", tone.className)} />
              <div className="grid min-w-0 gap-1">
                <ToastPrimitive.Title className="text-sm font-semibold">{item.title}</ToastPrimitive.Title>
                {item.description && (
                  <ToastPrimitive.Description className="text-sm text-text-muted">{item.description}</ToastPrimitive.Description>
                )}
                {item.action && (
                  <ToastPrimitive.Action
                    altText={item.action.label}
                    onClick={item.action.onClick}
                    className={cn("mt-1 justify-self-start text-sm font-medium text-primary underline-offset-4 hover:underline", focusRing)}
                  >
                    {item.action.label}
                  </ToastPrimitive.Action>
                )}
              </div>
              <ToastPrimitive.Close
                aria-label="Dismiss notification"
                className={cn("absolute right-2 top-2 inline-flex h-8 w-8 items-center justify-center rounded-md text-text-muted hover:bg-surface-muted hover:text-text", focusRing)}
              >
                <X size={16} aria-hidden="true" />
              </ToastPrimitive.Close>
            </ToastPrimitive.Root>
          );
        })}
        <ToastPrimitive.Viewport className="fixed bottom-0 right-0 z-[60] m-0 flex w-full max-w-sm list-none flex-col gap-2 p-4 outline-none" />
      </ToastPrimitive.Provider>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastApi {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used inside <ToastProvider>");
  return ctx;
}
