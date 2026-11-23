import type { AgentId } from "@/api/types";
import { cn } from "@/lib/cn";

import { agentIdentity } from "./agentIdentity";

const SIZES = { sm: { box: "h-7 w-7", icon: 14 }, md: { box: "h-9 w-9", icon: 18 }, lg: { box: "h-12 w-12", icon: 22 } };

/** The agent's icon in a circle of its accent colour, with its name as the accessible name. */
export function AgentAvatar({ agent, size = "md", className }: { agent: AgentId; size?: keyof typeof SIZES; className?: string }) {
  const identity = agentIdentity(agent);
  const Icon = identity.icon;
  const s = SIZES[size];
  return (
    <span
      role="img"
      aria-label={identity.displayName}
      data-agent={identity.id}
      className={cn("inline-flex shrink-0 items-center justify-center rounded-full text-agent-fg", identity.bgClass, s.box, className)}
    >
      <Icon size={s.icon} aria-hidden="true" />
    </span>
  );
}

/** Avatar + display name, e.g. in message headers. */
export function AgentLabel({ agent, className }: { agent: AgentId; className?: string }) {
  const identity = agentIdentity(agent);
  return (
    <span className={cn("inline-flex items-center gap-2", className)}>
      <AgentAvatar agent={agent} size="sm" />
      <span className={cn("text-sm font-semibold", identity.textClass)}>{identity.displayName}</span>
    </span>
  );
}
