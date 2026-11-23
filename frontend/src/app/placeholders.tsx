import type { UseQueryResult } from "@tanstack/react-query";
import { Building2, Compass, Construction, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import { isApiError } from "@/api/errors";
import { useCase } from "@/api/hooks";
import type { CaseView } from "@/api/types";
import { usePageTitle } from "@/brand";
import { EmptyState, ErrorState, LoadingBlock, buttonVariants } from "@/design";
import { cn } from "@/lib/cn";

/** Page frame: a heading and an optional lead, at a readable width. */
export function PageFrame({
  title,
  description,
  actions,
  children,
  width = "md",
}: {
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  width?: "md" | "lg";
}) {
  return (
    <div className={cn("mx-auto w-full px-4 py-8 sm:px-6 sm:py-10", width === "md" ? "max-w-4xl" : "max-w-6xl")}>
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div className="grid gap-1">
          <h1 className="text-2xl font-semibold text-text sm:text-3xl">{title}</h1>
          {description && <p className="max-w-2xl text-base text-text-muted">{description}</p>}
        </div>
        {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
      </div>
      {children}
    </div>
  );
}

/**
 * Loading (skeleton), error (friendly + retry) and empty states for any query (ADR-0019).
 * A 404 renders `notFound` when given.
 */
export function QueryStates<T>({
  query,
  loadingLabel,
  notFound,
  isEmpty,
  empty,
  children,
}: {
  query: UseQueryResult<T>;
  loadingLabel?: string;
  notFound?: ReactNode;
  isEmpty?: (data: T) => boolean;
  empty?: ReactNode;
  children: (data: T) => ReactNode;
}) {
  if (query.isPending) return <LoadingBlock label={loadingLabel} lines={4} />;
  if (query.isError) {
    if (notFound && isApiError(query.error) && query.error.isNotFound) return <>{notFound}</>;
    return <ErrorState error={query.error} onRetry={() => query.refetch()} retrying={query.isFetching} />;
  }
  if (empty && isEmpty?.(query.data)) return <>{empty}</>;
  return <>{children(query.data)}</>;
}

/** Unknown company id, or a company the user is not a member of (both are 404, ADR-0032). */
export function CompanyNotFound() {
  usePageTitle("Company not found");
  return (
    <div className="mx-auto w-full max-w-xl px-4 py-16" data-company-not-found="">
      <EmptyState
        icon={Building2}
        title="We couldn't find this company"
        description="It may have been deleted, or you may not be a member of it. Ask the owner to invite you if you think you should see it."
        action={
          <Link to="/app" className={buttonVariants({ variant: "primary" })}>
            Back to your companies
          </Link>
        }
      />
    </div>
  );
}

/** Placeholder content shown until a feature ticket replaces its folder (ADR-0035). */
export function ComingSoon({ title, description, icon = Construction }: { title: string; description: string; icon?: LucideIcon }) {
  return <EmptyState icon={icon} title={title} description={description} />;
}

/** A public or account page placeholder: title + empty state. */
export function PlaceholderPage({
  title,
  description,
  emptyTitle = "Nothing here yet",
  emptyDescription = "This page is on its way.",
  icon,
}: {
  title: string;
  description?: string;
  emptyTitle?: string;
  emptyDescription?: string;
  icon?: LucideIcon;
}) {
  return (
    <PageFrame title={title} description={description}>
      <ComingSoon title={emptyTitle} description={emptyDescription} icon={icon} />
    </PageFrame>
  );
}

/** A workspace view placeholder: loads the company, then shows the view's empty state. */
export function WorkspaceViewPlaceholder({
  caseId,
  title,
  description,
  icon = Compass,
  children,
}: {
  caseId: string;
  title: string;
  description: string;
  icon?: LucideIcon;
  children?: (view: CaseView) => ReactNode;
}) {
  const query = useCase(caseId);
  return (
    <section aria-labelledby={`view-${title}`} className="grid gap-4">
      <h2 id={`view-${title}`} className="text-xl font-semibold text-text">
        {title}
      </h2>
      <QueryStates query={query} loadingLabel={`Loading ${title.toLowerCase()}…`} notFound={<CompanyNotFound />}>
        {(view) => (children ? children(view) : <ComingSoon title={`No ${title.toLowerCase()} yet`} description={description} icon={icon} />)}
      </QueryStates>
    </section>
  );
}

/** Friendly 404 with links home (ADR-0035). */
export function NotFoundPage() {
  usePageTitle("Page not found");
  return (
    <div className="flex min-h-[60vh] items-center justify-center px-4 py-16" data-not-found="">
      <div className="w-full max-w-lg">
        <EmptyState
          icon={Compass}
          title="We couldn't find that page"
          description="The link may be out of date or mistyped."
          action={
            <>
              <Link to="/" className={buttonVariants({ variant: "primary" })}>
                Go to the home page
              </Link>
              <Link to="/app" className={buttonVariants({ variant: "secondary" })}>
                Your companies
              </Link>
            </>
          }
        />
      </div>
    </div>
  );
}
