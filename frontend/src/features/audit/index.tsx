import { History } from "lucide-react";

import { WorkspaceViewPlaceholder } from "@/app";

/** Placeholder for `features/audit` (T-020 replaces this folder; ADR-0035). */
export default function AuditView({ caseId }: { caseId: string }) {
  return (
    <WorkspaceViewPlaceholder
      caseId={caseId}
      title="Audit"
      description="Every signature and change will be listed here."
      icon={History}
    />
  );
}
