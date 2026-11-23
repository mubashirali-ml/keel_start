import { Users } from "lucide-react";

import { WorkspaceViewPlaceholder } from "@/app";

/** Placeholder for `features/team` (T-044 replaces this folder; ADR-0035). */
export default function TeamView({ caseId }: { caseId: string }) {
  return (
    <WorkspaceViewPlaceholder
      caseId={caseId}
      title="Team"
      description="Your co-founders and invitations will appear here."
      icon={Users}
    />
  );
}
