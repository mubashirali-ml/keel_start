import { useQueryClient } from "@tanstack/react-query";
import { ShieldOff } from "lucide-react";
import { useEffect, useRef, type ReactNode } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";

import { configureClient } from "@/api/client";
import { qk, useMe } from "@/api/hooks";
import type { MeView } from "@/api/types";
import { usePageTitle } from "@/brand";
import { EmptyState, ErrorState, LoadingBlock, buttonVariants } from "@/design";

/** `/login?next=<path>` for the current location. */
export function loginPath(next: string): string {
  return `/login?next=${encodeURIComponent(next)}`;
}

/** A safe in-app redirect target from `?next=` (no protocol-relative or external URLs). */
export function safeNext(next: string | null | undefined, fallback = "/app"): string {
  if (!next || !next.startsWith("/") || next.startsWith("//") || next.startsWith("/\\")) return fallback;
  return next;
}

const PUBLIC_PREFIXES = ["/login", "/signup", "/forgot-password", "/reset-password", "/verify-email"];

/**
 * Registers the client's 401 hook: any call that finds no session sends the browser to
 * `/login?next=<here>` (ADR-0035) and forgets the cached user.
 */
export function UnauthorizedRedirect() {
  const navigate = useNavigate();
  const location = useLocation();
  const qc = useQueryClient();
  const here = useRef(location);
  here.current = location;

  useEffect(() => {
    configureClient({
      onUnauthorized: () => {
        const { pathname, search } = here.current;
        qc.setQueryData(qk.me, null);
        if (PUBLIC_PREFIXES.some((p) => pathname.startsWith(p))) return;
        navigate(loginPath(pathname + search), { replace: true });
      },
    });
    return () => configureClient({ onUnauthorized: () => undefined });
  }, [navigate, qc]);
  return null;
}

/** Full-page placeholder while the session loads (same frame as the shell: no layout shift). */
export function SessionLoading() {
  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-10 sm:px-6">
      <LoadingBlock label="Checking your session…" lines={4} />
    </div>
  );
}

/** `/app/*` and `/admin/*`: a session is required; without one, go to the login page. */
export function RequireAuth({ children }: { children: (me: MeView) => ReactNode }) {
  const location = useLocation();
  const me = useMe();
  if (me.isPending) return <SessionLoading />;
  if (me.isError) {
    return (
      <div className="mx-auto w-full max-w-xl px-4 py-16">
        <ErrorState error={me.error} title="We couldn't check your session" onRetry={() => me.refetch()} retrying={me.isFetching} />
      </div>
    );
  }
  if (!me.data) return <Navigate to={loginPath(location.pathname + location.search)} replace />;
  return <>{children(me.data)}</>;
}

/** The admin area: admins only; everyone else gets a friendly "not available" page. */
export function RequireAdmin({ me, children }: { me: MeView; children: ReactNode }) {
  if (!me.user.is_admin) return <NotAvailablePage />;
  return <>{children}</>;
}

export function NotAvailablePage() {
  usePageTitle("Not available");
  return (
    <div className="mx-auto w-full max-w-xl px-4 py-16">
      <EmptyState
        icon={ShieldOff}
        title="This page isn't available"
        description="It's only open to the team that runs the service. If you think you should have access, contact support."
        action={
          <Link to="/app" className={buttonVariants({ variant: "primary" })}>
            Go to your companies
          </Link>
        }
      />
    </div>
  );
}

/** Login / sign-up / forgot password: logged-in users go straight to the app (or `?next=`). */
export function RedirectIfAuthed({ children }: { children: ReactNode }) {
  const location = useLocation();
  const me = useMe();
  if (me.data) {
    const next = new URLSearchParams(location.search).get("next");
    return <Navigate to={safeNext(next)} replace />;
  }
  return <>{children}</>;
}
