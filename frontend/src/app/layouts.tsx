import { Suspense, type ReactNode } from "react";
import { Link, NavLink, Outlet, useMatch } from "react-router-dom";

import { useCase, useMe } from "@/api/hooks";
import type { MeView } from "@/api/types";
import { Logo, TAGLINE, footerLine, useBrandName, useDisclaimer } from "@/brand";
import { LoadingBlock, buttonVariants, focusRing } from "@/design";
import { cn } from "@/lib/cn";

import { ActingFounderProvider } from "./ActingFounderContext";
import { AppBanners } from "./banners";
import { AccountMenu, CompanySwitcher, FounderSwitcher, HeaderProgress, HelpMenu } from "./header";
import { ThemeToggle } from "./theme";

export const MAIN_ID = "main-content";

/** First focusable element of every layout (WCAG 2.4.1). */
export function SkipLink() {
  return (
    <a
      href={`#${MAIN_ID}`}
      className={cn(
        "sr-only z-[80] rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-fg focus:not-sr-only focus:fixed focus:left-4 focus:top-3",
        focusRing,
      )}
    >
      Skip to content
    </a>
  );
}

/** Route-level loading frame for lazy pages: fixed height, so nothing jumps when it arrives. */
export function PageLoading() {
  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-10 sm:px-6">
      <LoadingBlock lines={4} />
    </div>
  );
}

function HomeLink({ to, markOnlyOnPhone = false }: { to: string; markOnlyOnPhone?: boolean }) {
  const brand = useBrandName();
  return (
    <Link to={to} className={cn("inline-flex shrink-0 items-center rounded-md", focusRing)} aria-label={`${brand} home`}>
      <Logo wordmarkClassName={markOnlyOnPhone ? "hidden sm:inline" : undefined} />
    </Link>
  );
}

// ---------------------------------------------------------------- Marketing
const MARKETING_NAV = [
  { to: "/pricing", label: "Pricing" },
  { to: "/security", label: "Security" },
];

export function MarketingLayout() {
  const brand = useBrandName();
  const disclaimer = useDisclaimer();
  const me = useMe();
  const loggedIn = !!me.data;
  return (
    <div data-layout="marketing" className="flex min-h-screen flex-col bg-bg">
      <SkipLink />
      <header className="sticky top-0 z-40 border-b bg-surface/90 backdrop-blur supports-[backdrop-filter]:bg-surface/80">
        <div className="mx-auto flex h-16 max-w-6xl items-center gap-4 px-4 sm:px-6">
          <HomeLink to="/" />
          <nav aria-label="Main" className="ml-4 hidden items-center gap-1 md:flex">
            {MARKETING_NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  cn(
                    "rounded-md px-3 py-2 text-sm font-medium transition-colors duration-fast",
                    isActive ? "text-primary" : "text-text-muted hover:text-text",
                    focusRing,
                  )
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-1 sm:gap-2">
            <ThemeToggle />
            {loggedIn ? (
              <Link to="/app" className={buttonVariants({ size: "sm" })}>
                Open app
              </Link>
            ) : (
              <>
                <Link to="/login" className={cn(buttonVariants({ variant: "ghost", size: "sm" }), "hidden sm:inline-flex")}>
                  Log in
                </Link>
                <Link to="/signup" className={buttonVariants({ size: "sm" })}>
                  Get started
                </Link>
              </>
            )}
          </div>
        </div>
      </header>
      <main id={MAIN_ID} tabIndex={-1} className="flex-1 outline-none">
        <Suspense fallback={<PageLoading />}>
          <Outlet />
        </Suspense>
      </main>
      <footer className="border-t bg-surface">
        <div className="mx-auto grid max-w-6xl gap-8 px-4 py-10 sm:px-6 md:grid-cols-[1fr_auto]">
          <div className="grid max-w-md gap-3">
            <Logo />
            <p className="text-sm text-text-muted">{TAGLINE}.</p>
            <p className="text-sm font-medium text-text" data-disclaimer="">
              {disclaimer}
            </p>
          </div>
          <nav aria-label="Footer" className="grid grid-cols-2 gap-x-10 gap-y-2 text-sm sm:grid-cols-3 md:grid-cols-2">
            {[
              ["/pricing", "Pricing"],
              ["/security", "Security"],
              ["/terms", "Terms"],
              ["/privacy", "Privacy"],
              ["/disclaimer", "Disclaimer"],
              ["/login", "Log in"],
            ].map(([to, label]) => (
              <Link key={to} to={to} className={cn("rounded-sm text-text-muted hover:text-text", focusRing)}>
                {label}
              </Link>
            ))}
          </nav>
        </div>
        <div className="border-t">
          <p className="mx-auto max-w-6xl px-4 py-4 text-xs text-text-muted sm:px-6">{footerLine(new Date().getFullYear(), brand)}</p>
        </div>
      </footer>
    </div>
  );
}

// ---------------------------------------------------------------- Auth (centered card)
export function AuthLayout() {
  const disclaimer = useDisclaimer();
  return (
    <div data-layout="auth" className="flex min-h-screen flex-col bg-bg">
      <SkipLink />
      <header className="mx-auto flex h-16 w-full max-w-5xl items-center justify-between px-4 sm:px-6">
        <HomeLink to="/" />
        <ThemeToggle />
      </header>
      <main id={MAIN_ID} tabIndex={-1} className="flex flex-1 items-start justify-center px-4 pb-12 pt-4 outline-none sm:items-center sm:pt-0">
        <div className="w-full max-w-md rounded-xl border bg-surface p-6 shadow-md sm:p-8">
          <Suspense fallback={<LoadingBlock lines={3} />}>
            <Outlet />
          </Suspense>
        </div>
      </main>
      <footer className="px-4 pb-6 text-center text-xs text-text-muted">{disclaimer}</footer>
    </div>
  );
}

// ---------------------------------------------------------------- App
function AppHeader({ me, caseId }: { me: MeView; caseId: string | null }) {
  const view = useCase(caseId ?? undefined).data ?? null;
  return (
    <header className="sticky top-0 z-40 border-b bg-surface">
      <div className="flex h-14 items-center gap-2 px-3 sm:gap-3 sm:px-4">
        <HomeLink to="/app" markOnlyOnPhone />
        <div className="ml-1 flex min-w-0 sm:ml-3">
          <CompanySwitcher me={me} current={caseId ? view : null} />
        </div>
        {view && <HeaderProgress view={view} />}
        <div className="ml-auto flex items-center gap-1 sm:gap-2">
          {view && (
            <div className="hidden md:block">
              <FounderSwitcher />
            </div>
          )}
          <HelpMenu me={me} />
          <ThemeToggle />
          <AccountMenu me={me} />
        </div>
      </div>
      {view && (
        <div className="border-t px-3 py-2 md:hidden">
          <FounderSwitcher />
        </div>
      )}
    </header>
  );
}

function CaseScope({ caseId, children }: { caseId: string | null; children: ReactNode }) {
  const view = useCase(caseId ?? undefined).data;
  if (!caseId || !view) return <>{children}</>;
  return (
    <ActingFounderProvider key={caseId} view={view}>
      {children}
    </ActingFounderProvider>
  );
}

/** Logged-in layout: header, account banners, then the page (workspace pages fill the height). */
export function AppShell({ me }: { me: MeView }) {
  const match = useMatch("/app/cases/:caseId/*");
  const caseId = match?.params.caseId ?? null;
  return (
    <CaseScope caseId={caseId}>
      <div data-layout="app" className={cn("flex flex-col bg-bg", caseId ? "h-dvh min-h-[32rem]" : "min-h-screen")}>
        <SkipLink />
        <AppHeader me={me} caseId={caseId} />
        <AppBanners me={me} />
        <main id={MAIN_ID} tabIndex={-1} className={cn("flex-1 outline-none", caseId && "min-h-0")}>
          <Suspense fallback={<PageLoading />}>
            <Outlet />
          </Suspense>
        </main>
      </div>
    </CaseScope>
  );
}

/** The `/design` gallery frame (no app chrome). */
export function BareLayout({ children }: { children: ReactNode }) {
  return (
    <div data-layout="bare" className="min-h-screen bg-bg">
      <SkipLink />
      {children}
    </div>
  );
}
