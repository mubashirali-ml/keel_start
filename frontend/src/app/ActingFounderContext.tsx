import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { useQueryClient } from "@tanstack/react-query";

import { caseIdFromPath, configureClient } from "@/api/client";
import { useConfig } from "@/api/hooks";
import type { CaseView, Founder } from "@/api/types";
import { STORAGE_KEYS, storage } from "@/lib/storage";

interface ActingFounderValue {
  /** True only in demo mode: the user may act as any founder of this company. */
  demo: boolean;
  /** The founder whose actions the user takes (their own founder outside demo mode). */
  founderId: string | null;
  founder: Founder | null;
  founders: Founder[];
  setFounderId: (id: string) => void;
}

const ActingFounderContext = createContext<ActingFounderValue>({
  demo: false,
  founderId: null,
  founder: null,
  founders: [],
  setFounderId: () => undefined,
});

function initialFounder(view: CaseView): string | null {
  const stored = storage.get(STORAGE_KEYS.founder(view.id));
  const ids = view.facts.founders.map((f) => f.id);
  if (stored && ids.includes(stored)) return stored;
  return view.my_founder_id ?? ids[0] ?? null;
}

/**
 * "Act as founder" (ADR-0035, demo mode only). Outside demo mode it just exposes the
 * user's own founder and sends nothing. In demo mode it keeps the choice per company in
 * localStorage `launch.founder.<caseId>` and the client sends it as `X-Act-As-Founder` on
 * every call for this company.
 */
export function ActingFounderProvider({ view, children }: { view: CaseView; children: ReactNode }) {
  const { data: config } = useConfig();
  const demo = !!config?.demo_mode;
  const [chosen, setChosen] = useState<string | null>(() => initialFounder(view));
  const founders = view.facts.founders;
  const founderId = demo ? chosen ?? view.my_founder_id ?? founders[0]?.id ?? null : view.my_founder_id;

  // Registered during render (idempotent), not in an effect: child views start fetching in
  // their own effects, which run before this provider's, and must already send the header.
  const registered = useRef<string | null>(null);
  const key = demo && founderId ? `${view.id}:${founderId}` : null;
  const register = () => {
    registered.current = key;
    configureClient({
      actAsFounder: key ? (path) => (caseIdFromPath(path) === view.id ? founderId : null) : () => null,
    });
  };
  if (registered.current !== key) register();

  const qc = useQueryClient();
  const previous = useRef(key);
  useEffect(() => {
    register();
    // A different acting founder sees the company differently (my_founder_id, what they
    // can sign): reload this company's data as that founder.
    if (previous.current !== key) qc.invalidateQueries({ queryKey: ["case", view.id] });
    previous.current = key;
    return () => {
      registered.current = null;
      configureClient({ actAsFounder: () => null });
    };
  }, [key]);

  const setFounderId = useCallback(
    (id: string) => {
      storage.set(STORAGE_KEYS.founder(view.id), id);
      setChosen(id);
    },
    [view.id],
  );

  const value = useMemo<ActingFounderValue>(
    () => ({
      demo,
      founderId,
      founder: founders.find((f) => f.id === founderId) ?? null,
      founders,
      setFounderId,
    }),
    [demo, founderId, founders, setFounderId],
  );
  return <ActingFounderContext.Provider value={value}>{children}</ActingFounderContext.Provider>;
}

export function useActingFounder(): ActingFounderValue {
  return useContext(ActingFounderContext);
}
