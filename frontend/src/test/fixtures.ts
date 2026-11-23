/** Sample API payloads for tests (the ADR-0036 demo: Alice Chen and Bob Diaz). */
import { DEFAULT_CONFIG } from "@/api/defaults";
import type { CaseSummary, CaseView, MeView, PublicConfig, Subscription } from "@/api/types";

export const subscription: Subscription = {
  user_id: "usr_alice0000001",
  plan: "launch",
  interval: "month",
  status: "active",
  current_period_end: "2026-12-23T00:00:00Z",
  cancel_at_period_end: false,
  provider_customer_id: null,
  provider_subscription_id: null,
};

export const caseSummary: CaseSummary = {
  id: "case_0123456789ab",
  company_name: "Acme Bakery Software",
  created_at: "2026-11-20T09:00:00Z",
  updated_at: "2026-11-22T09:00:00Z",
  percent: 33,
};

export function makeMe(overrides: Partial<MeView> = {}, user: Partial<MeView["user"]> = {}): MeView {
  return {
    user: {
      id: "usr_alice0000001",
      email: "alice@example.com",
      full_name: "Alice Chen",
      email_verified_at: "2026-11-20T09:00:00Z",
      is_admin: false,
      created_at: "2026-11-20T09:00:00Z",
      ...user,
    },
    plan: "launch",
    subscription,
    email_verified: true,
    companies: [caseSummary],
    csrf_token: "csrf-from-me",
    ...overrides,
  };
}

export function makeConfig(overrides: Partial<PublicConfig> = {}): PublicConfig {
  return { ...DEFAULT_CONFIG, ...overrides };
}

export function makeCase(overrides: Partial<CaseView> = {}): CaseView {
  return {
    id: caseSummary.id,
    created_at: caseSummary.created_at,
    updated_at: caseSummary.updated_at,
    facts: {
      business_description: "bookkeeping software for small bakeries",
      founders: [
        { id: "f1", name: "Alice Chen", email: "alice@example.com", equity_percent: "60", vesting_months: 48, cliff_months: 12 },
        { id: "f2", name: "Bob Diaz", email: "bob@example.com", equity_percent: "40", vesting_months: null, cliff_months: null },
      ],
      entity_type: "LLC",
      state: "WY",
      incorporation_date: "2026-12-01",
      name_preferences: [],
      company_name: "Acme Bakery Software",
      website: {
        pages: [],
        services: [],
        about: null,
        contact_email: null,
        contact_phone: null,
        contact_address: null,
        extra_content: [],
        style_notes: null,
      },
    },
    facts_locked: true,
    active_agent: "manager",
    company_name: "Acme Bakery Software",
    chosen_domain: null,
    validation_issues: [],
    missing_facts: [],
    deadline_83b: "2026-12-31",
    days_until_83b: 38,
    progress: {
      percent: 33,
      steps: [
        { id: "facts", label: "Facts", status: "done", detail: "" },
        { id: "name", label: "Name", status: "done", detail: "" },
        { id: "legal", label: "Legal", status: "in_progress", detail: "2 of 4 signed" },
        { id: "cap_table", label: "Cap table", status: "not_started", detail: "" },
        { id: "website", label: "Website", status: "not_started", detail: "" },
        { id: "registration", label: "Registration", status: "attention", detail: "83(b) due soon" },
      ],
    },
    legal_issues: [],
    my_role: "owner",
    my_founder_id: "f1",
    plan: "launch",
    active_jobs: [],
    ...overrides,
  };
}
