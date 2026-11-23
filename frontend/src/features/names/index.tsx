import { Tag } from "lucide-react";

import { WorkspaceViewPlaceholder } from "@/app";

/** Placeholder for `features/names` (T-019 replaces this folder; ADR-0035). */
export default function NamesView({ caseId }: { caseId: string }) {
  return (
    <WorkspaceViewPlaceholder
      caseId={caseId}
      title="Names"
      description="Name ideas with domain checks will appear here."
      icon={Tag}
    />
  );
}
