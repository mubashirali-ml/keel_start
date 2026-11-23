import { BrowserRouter } from "react-router-dom";

import { AppProviders, AppRoutes } from "@/app";

/** Providers (theme, React Query, tooltips, toasts) and the router (ADR-0019, ADR-0035). */
export default function App() {
  return (
    <AppProviders>
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <AppRoutes />
      </BrowserRouter>
    </AppProviders>
  );
}
