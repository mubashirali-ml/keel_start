import { Building2, ChevronsUpDown, CreditCard, HelpCircle, LayoutGrid, LifeBuoy, LogOut, Mail, Plus, Settings, Shield } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { findPlan, planName } from "@/api/defaults";
import { getLastApiError } from "@/api/errors";
import { useConfig, useLogout } from "@/api/hooks";
import { supportMailto } from "@/api/support";
import type { CaseView, MeView } from "@/api/types";
import { Avatar, Badge, IconButton, Menu, MenuContent, MenuItem, MenuLabel, MenuSeparator, MenuTrigger, Progress, Select, focusRing } from "@/design";
import { cn } from "@/lib/cn";

import { useActingFounder } from "./ActingFounderContext";

/** Company name or the friendly placeholder for a company that has no name yet. */
export function companyLabel(name: string | null | undefined): string {
  return name?.trim() || "New company";
}

// ---------------------------------------------------------------- company switcher
export function CompanySwitcher({ me, current }: { me: MeView; current: CaseView | null }) {
  const navigate = useNavigate();
  const label = current ? companyLabel(current.company_name) : "Your companies";
  return (
    <Menu>
      <MenuTrigger
        className={cn(
          "inline-flex h-9 min-w-0 max-w-full items-center gap-2 rounded-md border bg-surface px-2.5 text-sm font-medium text-text shadow-sm hover:bg-surface-muted sm:max-w-[14rem]",
          focusRing,
        )}
        aria-label={`Switch company. Current: ${label}`}
      >
        <Building2 size={16} aria-hidden="true" className="shrink-0 text-text-muted" />
        <span className="truncate">{label}</span>
        <ChevronsUpDown size={14} aria-hidden="true" className="shrink-0 text-text-muted" />
      </MenuTrigger>
      <MenuContent align="start" className="w-72">
        <MenuLabel>Your companies</MenuLabel>
        {me.companies.length === 0 && <p className="px-2.5 pb-2 text-sm text-text-muted">No companies yet.</p>}
        {me.companies.map((c) => (
          <MenuItem key={c.id} onSelect={() => navigate(`/app/cases/${c.id}/overview`)} icon={<Building2 size={16} />}>
            <span className="min-w-0 flex-1 truncate">{companyLabel(c.company_name)}</span>
            <span className="text-xs text-text-muted">{c.percent}%</span>
          </MenuItem>
        ))}
        <MenuSeparator />
        <MenuItem onSelect={() => navigate("/app")} icon={<LayoutGrid size={16} />}>
          All companies
        </MenuItem>
        <MenuItem onSelect={() => navigate("/app/onboarding")} icon={<Plus size={16} />}>
          New company
        </MenuItem>
      </MenuContent>
    </Menu>
  );
}

// ---------------------------------------------------------------- progress
export function HeaderProgress({ view }: { view: CaseView }) {
  return (
    <div className="hidden w-36 xl:block" data-header-progress="">
      <Progress value={view.progress.percent} label="Progress" showValue size="sm" />
    </div>
  );
}

// ---------------------------------------------------------------- founder switcher (demo only)
/** "Acting as" (ADR-0035): rendered only when `PublicConfig.demo_mode` is true. */
export function FounderSwitcher() {
  const { demo, founders, founderId, setFounderId } = useActingFounder();
  if (!demo || founders.length === 0) return null;
  return (
    <div className="flex items-center gap-2" data-founder-switcher="">
      <Badge tone="warning" size="sm">
        Demo mode
      </Badge>
      <label htmlFor="acting-founder" className="hidden text-sm text-text-muted 2xl:inline">
        Acting as
      </label>
      <Select
        id="acting-founder"
        aria-label="Acting as"
        className="h-9 w-40"
        value={founderId ?? undefined}
        onValueChange={setFounderId}
        options={founders.map((f) => ({ value: f.id, label: f.name }))}
      />
    </div>
  );
}

// ---------------------------------------------------------------- help menu
/** Help link and, when `support_email` is set, "Contact support" (ADR-0038; no reply times, ADR-0042). */
export function HelpMenu({ me }: { me: MeView | null }) {
  const navigate = useNavigate();
  const { data: config } = useConfig();
  const plans = config?.plans;
  const plan = planName(me?.plan ?? "free", plans);
  const email = config?.support_email;
  return (
    <Menu>
      <MenuTrigger asChild>
        <IconButton aria-label="Help" icon={<HelpCircle size={18} />} />
      </MenuTrigger>
      <MenuContent align="end">
        <MenuLabel>Help</MenuLabel>
        <MenuItem icon={<LifeBuoy size={16} />} onSelect={() => navigate("/pricing#faq")}>
          Help and questions
        </MenuItem>
        {email && (
          <MenuItem
            icon={<Mail size={16} />}
            onSelect={() => {
              window.location.href = supportMailto(email, plan, getLastApiError());
            }}
          >
            Contact support
          </MenuItem>
        )}
      </MenuContent>
    </Menu>
  );
}

// ---------------------------------------------------------------- account menu
export function AccountMenu({ me }: { me: MeView }) {
  const navigate = useNavigate();
  const logout = useLogout();
  const { data: config } = useConfig();
  const plan = findPlan(me.plan, config?.plans);
  return (
    <Menu>
      <MenuTrigger
        className={cn("inline-flex items-center gap-2 rounded-full p-0.5 pr-0.5 hover:bg-surface-muted sm:pr-2", focusRing)}
        aria-label={`Account: ${me.user.full_name}`}
      >
        <Avatar name={me.user.full_name} size="sm" />
        <span className="hidden max-w-[9rem] truncate text-sm font-medium text-text lg:inline">{me.user.full_name}</span>
      </MenuTrigger>
      <MenuContent align="end" className="w-64">
        <div className="grid gap-1 px-2.5 py-2">
          <span className="truncate text-sm font-semibold text-text">{me.user.full_name}</span>
          <span className="truncate text-xs text-text-muted">{me.user.email}</span>
          <span className="mt-1">
            <Badge tone={me.plan === "free" ? "neutral" : "primary"} size="sm">
              {`${plan?.name ?? "Free"} plan`}
            </Badge>
          </span>
        </div>
        <MenuSeparator />
        <MenuItem onSelect={() => navigate("/app/settings/profile")} icon={<Settings size={16} />}>
          Settings
        </MenuItem>
        <MenuItem onSelect={() => navigate("/app/settings/billing")} icon={<CreditCard size={16} />}>
          Plan and billing
        </MenuItem>
        {me.user.is_admin && (
          <MenuItem onSelect={() => navigate("/admin")} icon={<Shield size={16} />}>
            Admin
          </MenuItem>
        )}
        <MenuSeparator />
        <MenuItem
          icon={<LogOut size={16} />}
          onSelect={() =>
            logout.mutate(undefined, {
              onSettled: () => navigate("/login", { replace: true }),
            })
          }
        >
          Log out
        </MenuItem>
      </MenuContent>
    </Menu>
  );
}

