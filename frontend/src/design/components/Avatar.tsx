import * as AvatarPrimitive from "@radix-ui/react-avatar";

import { cn } from "@/lib/cn";

const SIZES = { sm: "h-7 w-7 text-xs", md: "h-9 w-9 text-sm", lg: "h-12 w-12 text-base" };

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return "?";
  const first = parts[0][0] ?? "";
  const last = parts.length > 1 ? parts[parts.length - 1][0] ?? "" : "";
  return (first + last).toUpperCase();
}

export interface AvatarProps {
  name: string;
  src?: string | null;
  size?: keyof typeof SIZES;
  className?: string;
}

/** A person's picture, falling back to their initials. */
export function Avatar({ name, src, size = "md", className }: AvatarProps) {
  return (
    <AvatarPrimitive.Root
      className={cn("inline-flex shrink-0 select-none items-center justify-center overflow-hidden rounded-full bg-primary-soft font-semibold text-primary", SIZES[size], className)}
      aria-label={name}
      role="img"
    >
      {src && <AvatarPrimitive.Image src={src} alt="" className="h-full w-full object-cover" />}
      <AvatarPrimitive.Fallback aria-hidden="true">{initials(name)}</AvatarPrimitive.Fallback>
    </AvatarPrimitive.Root>
  );
}
