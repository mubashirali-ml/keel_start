import { Sparkles } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import { DEFAULT_PLANS } from "@/api/defaults";
import { isApiError, type ApiError } from "@/api/errors";
import { useConfig } from "@/api/hooks";
import type { Plan, PlanId } from "@/api/types";
import { cn } from "@/lib/cn";

import { buttonVariants } from "./Button";

export function isPlanRequired(error: unknown): error is ApiError {
  return isApiError(error) && error.code === "plan_required";
}

function joinNames(names: string[]): string {
  if (names.length <= 1) return names[0] ?? "";
  return `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}`;
}

export interface PlanGateCopy {
  heading: string;
  message: string;
  plan: Plan;
}

/**
 * Upgrade copy for a `plan_required` error (ADR-0035, ADR-0038). The plan comes from
 * `details.required_plan` (falling back to Launch). A feature gate (`details.feature`)
 * names every plan that has it ("Available on Launch and Team"); the company limit names
 * the next plan ("Upgrade to Team for more companies").
 */
export function planGateCopy(error: ApiError, plans: Plan[] = DEFAULT_PLANS): PlanGateCopy {
  const all = (plans.length ? plans : DEFAULT_PLANS).slice().sort((a, b) => a.rank - b.rank);
  const wanted = typeof error.details.required_plan === "string" ? (error.details.required_plan as PlanId) : "launch";
  const plan = all.find((p) => p.id === wanted) ?? all.find((p) => p.id === "launch") ?? DEFAULT_PLANS[1];
  const isFeature = typeof error.details.feature === "string";
  const heading = isFeature
    ? `Available on ${joinNames(all.filter((p) => p.rank >= plan.rank).map((p) => p.name))}`
    : `Upgrade to ${plan.name} for more companies`;
  return { heading, message: error.message, plan };
}

export interface PlanGateProps {
  /** The error of the gated action (e.g. a mutation's `error`). */
  error?: unknown;
  /** The action itself; stays visible above the prompt. */
  children?: ReactNode;
  className?: string;
}

/** Wraps an action whose API call can return `plan_required` and shows what upgrading unlocks. */
export function PlanGate({ error, children, className }: PlanGateProps) {
  const { data: config } = useConfig();
  if (!isPlanRequired(error)) return <>{children}</>;
  const copy = planGateCopy(error, config?.plans);
  return (
    <div className={cn("grid gap-3", className)}>
      {children}
      <div
        role="status"
        data-plan-gate={copy.plan.id}
        className="flex flex-col gap-3 rounded-lg border border-primary/30 bg-primary-soft p-4 sm:flex-row sm:items-center sm:justify-between"
      >
        <div className="flex items-start gap-3">
          <Sparkles size={20} aria-hidden="true" className="mt-0.5 shrink-0 text-primary" />
          <div className="grid gap-0.5">
            <p className="text-sm font-semibold text-text">{copy.heading}</p>
            <p className="text-sm text-text">{copy.message}</p>
          </div>
        </div>
        <Link to="/pricing" className={cn(buttonVariants({ variant: "primary", size: "sm" }), "self-start sm:self-auto")}>
          See plans
        </Link>
      </div>
    </div>
  );
}
