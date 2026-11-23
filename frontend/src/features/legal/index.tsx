import { FileSignature } from "lucide-react";

import { WorkspaceViewPlaceholder } from "@/app";

/** Placeholder for `features/legal` (T-020 replaces this folder; ADR-0035). */
export default function LegalView({ caseId }: { caseId: string }) {
  return (
    <WorkspaceViewPlaceholder
      caseId={caseId}
      title="Legal"
      description="Your founding documents and signatures will appear here."
      icon={FileSignature}
    />
  );
}
