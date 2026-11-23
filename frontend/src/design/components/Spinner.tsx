import { Loader2 } from "lucide-react";

import { cn } from "@/lib/cn";

export function Spinner({ size = 16, className, label }: { size?: number; className?: string; label?: string }) {
  return (
    <Loader2
      size={size}
      className={cn("shrink-0 animate-spin motion-reduce:animate-none", className)}
      aria-hidden={label ? undefined : true}
      aria-label={label}
      role={label ? "img" : undefined}
    />
  );
}
