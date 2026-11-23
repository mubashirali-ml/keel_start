import { LayoutDashboard } from "lucide-react";

import { WorkspaceViewPlaceholder } from "@/app";

/** Placeholder for `features/overview` (T-018 replaces this folder; ADR-0035). */
export default function OverviewView({ caseId }: { caseId: string }) {
  return (
    <WorkspaceViewPlaceholder
      caseId={caseId}
      title="Overview"
      description="A summary of your company and what to do next will appear here."
      icon={LayoutDashboard}
    />
  );
}
