import { PieChart } from "lucide-react";

import { WorkspaceViewPlaceholder } from "@/app";

/** Placeholder for `features/cap-table` (T-021 replaces this folder; ADR-0035). */
export default function CapTableView({ caseId }: { caseId: string }) {
  return (
    <WorkspaceViewPlaceholder
      caseId={caseId}
      title="Cap table"
      description="Who owns what, with vesting schedules, will appear here."
      icon={PieChart}
    />
  );
}
