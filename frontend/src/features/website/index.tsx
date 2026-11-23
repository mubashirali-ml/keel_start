import { Globe } from "lucide-react";

import { WorkspaceViewPlaceholder } from "@/app";

/** Placeholder for `features/website` (T-022 replaces this folder; ADR-0035). */
export default function WebsiteView({ caseId }: { caseId: string }) {
  return (
    <WorkspaceViewPlaceholder
      caseId={caseId}
      title="Website"
      description="Your website preview and publishing will appear here."
      icon={Globe}
    />
  );
}
