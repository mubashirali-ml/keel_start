import { render, type RenderResult } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";

import { AppProviders, AppRoutes, createQueryClient } from "@/app";

/** Shows the current location so tests can assert redirects. */
export function LocationProbe() {
  const location = useLocation();
  return <output data-testid="location">{location.pathname + location.search}</output>;
}

/** Renders `ui` with every provider and a memory router at `route`. */
export function renderWithProviders(ui: ReactElement, { route = "/" }: { route?: string } = {}): RenderResult {
  const client = createQueryClient();
  return render(
    <AppProviders queryClient={client}>
      <MemoryRouter initialEntries={[route]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Routes>
          <Route path="*" element={ui} />
        </Routes>
        <LocationProbe />
      </MemoryRouter>
    </AppProviders>,
  );
}

/** Renders the whole app (all routes and layouts) at `route`. */
export function renderApp(route: string): RenderResult {
  const client = createQueryClient();
  return render(
    <AppProviders queryClient={client}>
      <MemoryRouter initialEntries={[route]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <AppRoutes />
        <LocationProbe />
      </MemoryRouter>
    </AppProviders>,
  );
}
