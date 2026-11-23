import { CheckCircle2, CircleDashed, Clock, Loader2, PenLine, Rocket, XCircle, type LucideIcon } from "lucide-react";

import type { DocumentStatus, DomainStatus, JobStatus, SiteBuildStatus, StepStatus } from "@/api/types";

import { Badge, type BadgeTone } from "./Badge";

interface StatusStyle {
  tone: BadgeTone;
  label: string;
  icon?: LucideIcon;
}

/** Tone + label for every status the API returns (ADR-0019). */
export const STATUS_STYLES = {
  step: {
    not_started: { tone: "neutral", label: "Not started", icon: CircleDashed },
    in_progress: { tone: "info", label: "In progress", icon: Clock },
    done: { tone: "success", label: "Done" },
    attention: { tone: "warning", label: "Needs attention" },
  } satisfies Record<StepStatus, StatusStyle>,
  document: {
    awaiting_signatures: { tone: "warning", label: "Awaiting signatures", icon: PenLine },
    executed: { tone: "success", label: "Signed by everyone" },
  } satisfies Record<DocumentStatus, StatusStyle>,
  domain: {
    available: { tone: "success", label: "Available" },
    taken: { tone: "danger", label: "Taken" },
    unknown: { tone: "neutral", label: "Couldn't check" },
  } satisfies Record<DomainStatus, StatusStyle>,
  site: {
    qa_passed: { tone: "success", label: "Passed checks" },
    qa_failed: { tone: "warning", label: "Needs fixes" },
    deployed: { tone: "success", label: "Live", icon: Rocket },
    deploy_failed: { tone: "danger", label: "Publishing failed" },
    deploy_not_configured: { tone: "info", label: "Preview only" },
  } satisfies Record<SiteBuildStatus, StatusStyle>,
  job: {
    queued: { tone: "neutral", label: "Waiting", icon: Clock },
    running: { tone: "info", label: "Working on it", icon: Loader2 },
    succeeded: { tone: "success", label: "Finished", icon: CheckCircle2 },
    failed: { tone: "danger", label: "Failed", icon: XCircle },
    cancelled: { tone: "neutral", label: "Cancelled" },
  } satisfies Record<JobStatus, StatusStyle>,
} as const;

export type StatusBadgeProps =
  | { kind: "step"; status: StepStatus; className?: string }
  | { kind: "document"; status: DocumentStatus; className?: string }
  | { kind: "domain"; status: DomainStatus; className?: string }
  | { kind: "site"; status: SiteBuildStatus; className?: string }
  | { kind: "job"; status: JobStatus; className?: string };

export function StatusBadge(props: StatusBadgeProps) {
  const table = STATUS_STYLES[props.kind] as Record<string, StatusStyle>;
  const style = table[props.status] ?? { tone: "neutral" as const, label: String(props.status) };
  return (
    <Badge tone={style.tone} icon={style.icon} className={props.className}>
      {style.label}
    </Badge>
  );
}
