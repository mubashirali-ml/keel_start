import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

import { ToastProvider, TooltipProvider } from "@/design";

import { ThemeProvider } from "./theme";

/** React Query defaults: the client already retries GETs on network errors (ADR-0023). */
export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, refetchOnWindowFocus: false, staleTime: 15_000 },
      mutations: { retry: false },
    },
  });
}

/** Theme, server state, tooltips and toasts (the router is added by the caller). */
export function AppProviders({ children, queryClient }: { children: ReactNode; queryClient?: QueryClient }) {
  const [client] = useState(() => queryClient ?? createQueryClient());
  return (
    <ThemeProvider>
      <QueryClientProvider client={client}>
        <TooltipProvider delayDuration={300}>
          <ToastProvider>{children}</ToastProvider>
        </TooltipProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
