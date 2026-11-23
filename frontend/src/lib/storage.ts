/** localStorage that never throws (private mode, blocked storage). */
export const storage = {
  get(key: string): string | null {
    try {
      return window.localStorage.getItem(key);
    } catch {
      return null;
    }
  },
  set(key: string, value: string): void {
    try {
      window.localStorage.setItem(key, value);
    } catch {
      /* ignore */
    }
  },
  remove(key: string): void {
    try {
      window.localStorage.removeItem(key);
    } catch {
      /* ignore */
    }
  },
};

/** Storage keys (internal names, never shown to customers; ADR-0041). */
export const STORAGE_KEYS = {
  theme: "launch.theme",
  founder: (caseId: string) => `launch.founder.${caseId}`,
  mobilePane: "launch.mobile-pane",
} as const;
