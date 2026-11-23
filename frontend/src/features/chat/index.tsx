import { MessageSquare } from "lucide-react";

import { AgentAvatar, agentIdentity } from "@/agents";
import { useCase } from "@/api/hooks";
import { CompanyNotFound, QueryStates } from "@/app";
import { EmptyState } from "@/design";

/**
 * Placeholder for `features/chat` (T-018 replaces this folder; ADR-0035). The shell renders
 * the default export in the chat panel with `{ caseId }`.
 */
export default function ChatPanel({ caseId }: { caseId: string }) {
  const query = useCase(caseId);
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex items-center gap-3 border-b px-4 py-3">
        <QueryStates query={query} loadingLabel="Loading the chat…" notFound={<CompanyNotFound />}>
          {(view) => (
            <>
              <AgentAvatar agent={view.active_agent} />
              <div className="grid">
                <span className="text-sm font-semibold text-text">{agentIdentity(view.active_agent).displayName}</span>
                <span className="text-xs text-text-muted">is with you</span>
              </div>
            </>
          )}
        </QueryStates>
      </div>
      <div className="flex flex-1 items-center justify-center p-4">
        <EmptyState
          icon={MessageSquare}
          title="No messages yet"
          description="Your conversation with the Manager and the specialist agents will appear here."
          className="w-full"
        />
      </div>
    </div>
  );
}
