import * as MenuPrimitive from "@radix-ui/react-dropdown-menu";
import { Check, Monitor, Moon, Sun } from "lucide-react";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { IconButton, MenuContent } from "@/design";
import { cn } from "@/lib/cn";
import { STORAGE_KEYS, storage } from "@/lib/storage";
import { QUERIES, useMediaQuery } from "@/lib/useMediaQuery";

export type ThemeChoice = "light" | "dark" | "system";

interface ThemeContextValue {
  choice: ThemeChoice;
  resolved: "light" | "dark";
  setChoice: (choice: ThemeChoice) => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function readThemeChoice(): ThemeChoice {
  const stored = storage.get(STORAGE_KEYS.theme);
  return stored === "light" || stored === "dark" || stored === "system" ? stored : "system";
}

/** Applies the theme as the `dark` class on <html> (the same rule as public/theme-init.js). */
export function applyTheme(resolved: "light" | "dark") {
  const root = document.documentElement;
  root.classList.toggle("dark", resolved === "dark");
  root.style.colorScheme = resolved;
}

/**
 * Theme state (ADR-0019): `system` by default, persisted in localStorage `launch.theme`.
 * public/theme-init.js applies it before first paint, so this only keeps it in sync.
 */
export function ThemeProvider({ children }: { children: ReactNode }) {
  const [choice, setChoiceState] = useState<ThemeChoice>(readThemeChoice);
  const systemDark = useMediaQuery(QUERIES.prefersDark);
  const resolved: "light" | "dark" = choice === "system" ? (systemDark ? "dark" : "light") : choice;

  useEffect(() => applyTheme(resolved), [resolved]);

  const setChoice = useCallback((next: ThemeChoice) => {
    storage.set(STORAGE_KEYS.theme, next);
    setChoiceState(next);
  }, []);

  const value = useMemo(() => ({ choice, resolved, setChoice }), [choice, resolved, setChoice]);
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used inside <ThemeProvider>");
  return ctx;
}

const OPTIONS: { value: ThemeChoice; label: string; icon: typeof Sun }[] = [
  { value: "light", label: "Light", icon: Sun },
  { value: "dark", label: "Dark", icon: Moon },
  { value: "system", label: "System", icon: Monitor },
];

/** Header control: Light / Dark / System. */
export function ThemeToggle({ className }: { className?: string }) {
  const { choice, resolved, setChoice } = useTheme();
  const CurrentIcon = resolved === "dark" ? Moon : Sun;
  const label = OPTIONS.find((o) => o.value === choice)?.label ?? "System";
  return (
    <MenuPrimitive.Root>
      <MenuPrimitive.Trigger asChild>
        <IconButton
          aria-label={`Theme: ${label}. Change theme`}
          icon={<CurrentIcon size={18} />}
          className={className}
          data-theme-toggle=""
        />
      </MenuPrimitive.Trigger>
      <MenuContent align="end" className="min-w-[10rem]">
        <MenuPrimitive.Label className="px-2.5 py-2 text-xs text-text-muted">Theme</MenuPrimitive.Label>
        <MenuPrimitive.RadioGroup value={choice} onValueChange={(v) => setChoice(v as ThemeChoice)}>
          {OPTIONS.map(({ value, label: text, icon: Icon }) => (
            <MenuPrimitive.RadioItem
              key={value}
              value={value}
              className={cn(
                "flex cursor-pointer select-none items-center gap-2.5 rounded-sm px-2.5 py-2 outline-none data-[highlighted]:bg-primary-soft",
              )}
            >
              <Icon size={16} aria-hidden="true" className="text-text-muted" />
              <span className="flex-1">{text}</span>
              <MenuPrimitive.ItemIndicator>
                <Check size={16} aria-hidden="true" className="text-primary" />
              </MenuPrimitive.ItemIndicator>
            </MenuPrimitive.RadioItem>
          ))}
        </MenuPrimitive.RadioGroup>
      </MenuContent>
    </MenuPrimitive.Root>
  );
}
