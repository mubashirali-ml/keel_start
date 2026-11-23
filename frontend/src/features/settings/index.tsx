/**
 * Placeholder pages for `features/settings` (T-044 replaces this folder; ADR-0035).
 * Named exports: SettingsPage (`profile`, `security`, `billing`, `privacy`), TestCheckoutPage.
 */
import { CreditCard, Lock, ShieldCheck, User } from "lucide-react";
import { NavLink, useParams } from "react-router-dom";

import { useSubscription } from "@/api/hooks";
import { SETTINGS_SECTIONS, type SettingsSection } from "@/api/types";
import { ComingSoon, PageFrame, QueryStates } from "@/app";
import { Badge, focusRing } from "@/design";
import { cn } from "@/lib/cn";

const SECTIONS: Record<SettingsSection, { label: string; icon: typeof User; text: string }> = {
  profile: { label: "Profile", icon: User, text: "Your name and email will be editable here." },
  security: { label: "Security", icon: Lock, text: "Password and sessions will be managed here." },
  billing: { label: "Plan and billing", icon: CreditCard, text: "Your plan, usage and invoices will appear here." },
  privacy: { label: "Privacy", icon: ShieldCheck, text: "Export or delete your data here." },
};

function BillingPlaceholder() {
  const overview = useSubscription();
  return (
    <QueryStates query={overview} loadingLabel="Loading your plan…">
      {(data) => (
        <div className="grid gap-3">
          <Badge tone="primary">{`${data.plan.name} plan`}</Badge>
          <ComingSoon title="Billing details are on their way" description={SECTIONS.billing.text} icon={CreditCard} />
        </div>
      )}
    </QueryStates>
  );
}

export function SettingsPage() {
  const { section = "profile" } = useParams();
  const current = (SETTINGS_SECTIONS as readonly string[]).includes(section) ? (section as SettingsSection) : "profile";
  const meta = SECTIONS[current];
  return (
    <PageFrame title="Settings" width="lg">
      <div className="grid gap-6 md:grid-cols-[12rem_1fr]">
        <nav aria-label="Settings" className="flex gap-1 overflow-x-auto md:flex-col">
          {SETTINGS_SECTIONS.map((s) => {
            const Icon = SECTIONS[s].icon;
            return (
              <NavLink
                key={s}
                to={`/app/settings/${s}`}
                className={({ isActive }) =>
                  cn(
                    "inline-flex shrink-0 items-center gap-2 rounded-md px-3 py-2 text-sm font-medium",
                    isActive || s === current ? "bg-primary-soft text-primary" : "text-text-muted hover:bg-surface-muted hover:text-text",
                    focusRing,
                  )
                }
              >
                <Icon size={16} aria-hidden="true" />
                {SECTIONS[s].label}
              </NavLink>
            );
          })}
        </nav>
        <section aria-labelledby="settings-heading" className="grid content-start gap-4">
          <h2 id="settings-heading" className="text-xl font-semibold text-text">
            {meta.label}
          </h2>
          {current === "billing" ? <BillingPlaceholder /> : <ComingSoon title={`${meta.label} settings are on their way`} description={meta.text} icon={meta.icon} />}
        </section>
      </div>
    </PageFrame>
  );
}

export function TestCheckoutPage() {
  return (
    <PageFrame title="Test checkout" description="Payments are simulated in test mode; no card is charged.">
      <ComingSoon title="Test checkout is on its way" description="You'll confirm a simulated payment here." icon={CreditCard} />
    </PageFrame>
  );
}
