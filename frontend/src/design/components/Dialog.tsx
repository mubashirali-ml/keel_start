import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { useState, type ReactNode } from "react";

import { cn } from "@/lib/cn";

import { focusRing } from "../focus";
import { Button } from "./Button";

/**
 * Modal dialog (Radix): focus is trapped inside while open, Escape and the close button
 * close it, focus returns to the trigger afterwards.
 */
export const Dialog = DialogPrimitive.Root;
export const DialogTrigger = DialogPrimitive.Trigger;
export const DialogClose = DialogPrimitive.Close;

export interface DialogContentProps {
  title: ReactNode;
  description?: ReactNode;
  children?: ReactNode;
  footer?: ReactNode;
  size?: "sm" | "md" | "lg";
  className?: string;
  /** Hide the corner close button (e.g. while a request is running). */
  hideClose?: boolean;
}

const SIZES = { sm: "max-w-sm", md: "max-w-lg", lg: "max-w-2xl" };

export function DialogContent({ title, description, children, footer, size = "md", className, hideClose }: DialogContentProps) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-text/40 backdrop-blur-[2px] animate-fade-in" />
      <DialogPrimitive.Content
        className={cn(
          "fixed left-1/2 top-1/2 z-50 flex max-h-[calc(100dvh-2rem)] w-[calc(100vw-2rem)] -translate-x-1/2 -translate-y-1/2 flex-col",
          "rounded-lg border bg-surface-raised text-text shadow-lg animate-scale-in focus:outline-none",
          SIZES[size],
          className,
        )}
        {...(description ? {} : { "aria-describedby": undefined })}
      >
        <div className="flex items-start justify-between gap-4 p-5 pb-2">
          <div className="grid gap-1">
            <DialogPrimitive.Title className="text-lg font-semibold leading-7">{title}</DialogPrimitive.Title>
            {description && (
              <DialogPrimitive.Description className="text-sm text-text-muted">{description}</DialogPrimitive.Description>
            )}
          </div>
          {!hideClose && (
            <DialogPrimitive.Close
              aria-label="Close"
              className={cn("-mr-2 -mt-1 inline-flex h-9 w-9 items-center justify-center rounded-md text-text-muted hover:bg-surface-muted hover:text-text", focusRing)}
            >
              <X size={18} aria-hidden="true" />
            </DialogPrimitive.Close>
          )}
        </div>
        {children && <div className="overflow-y-auto px-5 py-3">{children}</div>}
        {footer && <div className="flex flex-col-reverse gap-2 border-t p-4 sm:flex-row sm:justify-end">{footer}</div>}
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}

export interface ConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: ReactNode;
  description?: ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  tone?: "primary" | "danger";
  /** May return a promise: the confirm button shows a spinner until it settles. */
  onConfirm: () => void | Promise<unknown>;
  children?: ReactNode;
}

/** "Are you sure?" with a clear confirm and cancel; danger tone for destructive actions. */
export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  tone = "primary",
  onConfirm,
  children,
}: ConfirmDialogProps) {
  const [busy, setBusy] = useState(false);
  const confirm = async () => {
    setBusy(true);
    try {
      await onConfirm();
      onOpenChange(false);
    } catch {
      /* the caller shows the error; keep the dialog open */
    } finally {
      setBusy(false);
    }
  };
  return (
    <Dialog open={open} onOpenChange={(next) => !busy && onOpenChange(next)}>
      <DialogContent
        size="sm"
        title={title}
        description={description}
        hideClose={busy}
        footer={
          <>
            <DialogClose asChild>
              <Button variant="secondary" disabled={busy}>
                {cancelLabel}
              </Button>
            </DialogClose>
            <Button variant={tone} loading={busy} onClick={confirm}>
              {confirmLabel}
            </Button>
          </>
        }
      >
        {children}
      </DialogContent>
    </Dialog>
  );
}
