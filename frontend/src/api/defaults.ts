/**
 * Compiled defaults for `PublicConfig` (ADR-0035): used until `GET /api/config` answers,
 * and whenever it can't be reached. Mirrors `build_plans()` with the default amounts
 * (ADR-0038) and the support labels of ADR-0042 (no promised reply times).
 */

import { BRAND_FALLBACK_NAME } from "@/brand/brand";

import type { Feature, Plan, PlanId, PublicConfig } from "./types";

const PAID: Feature[] = ["documents", "esign", "signed_pdf", "website_deploy"];

export const DEFAULT_PLANS: Plan[] = [
  {
    id: "free",
    rank: 0,
    name: "Free",
    tagline: "Plan your company with every agent, free.",
    price_month_cents: 0,
    price_year_cents: 0,
    yearly_available: false,
    features: [],
    max_companies: 1,
    llm_calls_per_month: 300,
    support: "basic",
    support_label: "Email support",
    highlights: [
      "1 company",
      "300 AI messages a month",
      "Chat with every agent, legal Q&A and name ideas with live domain checks",
      "Cap table with CSV and Excel downloads",
      "Website preview and .zip download",
      "Registration checklist and 83(b) reminders",
      "Co-founders join free, unlimited",
      "Email support",
    ],
  },
  {
    id: "launch",
    rank: 1,
    name: "Launch",
    tagline: "Form your company: documents, e-signatures and a live website.",
    price_month_cents: 2900,
    price_year_cents: 29000,
    yearly_available: true,
    features: [...PAID],
    max_companies: 3,
    llm_calls_per_month: 2000,
    support: "standard",
    support_label: "Email support",
    highlights: [
      "Everything in Free",
      "Up to 3 companies",
      "2,000 AI messages a month",
      "Founding documents drafted",
      "Electronic signatures",
      "Signed PDF and Word downloads",
      "Website publishing",
      "Co-founders join free, unlimited",
      "Email support",
    ],
  },
  {
    id: "team",
    rank: 2,
    name: "Team",
    tagline: "For serial founders, studios and advisers who set up several companies.",
    price_month_cents: 7900,
    price_year_cents: 79000,
    yearly_available: true,
    features: [...PAID],
    max_companies: 15,
    llm_calls_per_month: 10000,
    support: "priority",
    support_label: "Priority support",
    highlights: [
      "Everything in Launch",
      "Up to 15 companies",
      "10,000 AI messages a month",
      "Co-founders join free, unlimited",
      "Priority support",
    ],
  },
];

export const DEFAULT_CONFIG: PublicConfig = {
  brand_name: BRAND_FALLBACK_NAME,
  demo_mode: false,
  payments_test_mode: false,
  hosting_configured: false,
  plans: DEFAULT_PLANS,
  esign_consent_text:
    "I agree to sign this document electronically. I understand my typed name is my signature and has the " +
    "same effect as a handwritten signature, and that a record of this signature (time, account, IP address " +
    "and a fingerprint of the document) is kept.",
  esign_consent_version: "2026-11-23",
  support_email: null,
  yearly_enabled: true,
};

/** The plan with `id` from `plans`, falling back to the compiled defaults. */
export function findPlan(id: PlanId | string | null | undefined, plans: Plan[] = DEFAULT_PLANS): Plan | undefined {
  return plans.find((p) => p.id === id) ?? DEFAULT_PLANS.find((p) => p.id === id);
}

export function planName(id: PlanId | string | null | undefined, plans: Plan[] = DEFAULT_PLANS): string {
  return findPlan(id, plans)?.name ?? "Free";
}
