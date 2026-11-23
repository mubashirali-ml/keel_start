import { ListChecks } from "lucide-react";

import { WorkspaceViewPlaceholder } from "@/app";

/** Placeholder for `features/guide` (T-019 replaces this folder; ADR-0035). */
export default function GuideView({ caseId }: { caseId: string }) {
  return (
    <WorkspaceViewPlaceholder
      caseId={caseId}
      title="Guide"
      description="Your registration checklist will appear here."
      icon={ListChecks}
    />
  );
}
