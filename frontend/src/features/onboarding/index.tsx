/**
 * Placeholder pages for `features/onboarding` (T-036 replaces this folder; ADR-0035).
 * Named exports: CompaniesPage, OnboardingPage.
 */
import { Building2, Plus, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";

import { useCases } from "@/api/hooks";
import { PageFrame, PlaceholderPage, QueryStates, companyLabel } from "@/app";
import { Card, EmptyState, Progress, buttonVariants } from "@/design";
import { formatDate } from "@/lib/format";

export function CompaniesPage() {
  const cases = useCases();
  const newCompany = (
    <Link to="/app/onboarding" className={buttonVariants()}>
      <Plus size={18} aria-hidden="true" />
      New company
    </Link>
  );
  return (
    <PageFrame title="Your companies" description="Pick up where you left off, or start a new company." actions={newCompany}>
      <QueryStates
        query={cases}
        loadingLabel="Loading your companies…"
        isEmpty={(list) => list.length === 0}
        empty={
          <EmptyState
            icon={Building2}
            title="No companies yet"
            description="Start your first company and meet your agents."
            action={newCompany}
          />
        }
      >
        {(list) => (
          <ul className="grid gap-3 sm:grid-cols-2">
            {list.map((c) => (
              <li key={c.id}>
                <Card className="p-4">
                  <Link to={`/app/cases/${c.id}/overview`} className="grid gap-3 rounded-md focus-visible:outline-none">
                    <span className="text-base font-semibold text-text">{companyLabel(c.company_name)}</span>
                    <Progress value={c.percent} label={`${companyLabel(c.company_name)} progress`} showValue size="sm" />
                    <span className="text-xs text-text-muted">Updated {formatDate(c.updated_at)}</span>
                  </Link>
                </Card>
              </li>
            ))}
          </ul>
        )}
      </QueryStates>
    </PageFrame>
  );
}

export function OnboardingPage() {
  return (
    <PlaceholderPage
      title="Start a company"
      description="Describe your company, meet your agents, then start your first chat."
      emptyTitle="Getting started is on its way"
      emptyDescription="You'll describe your business here and the Manager will take it from there."
      icon={Sparkles}
    />
  );
}
