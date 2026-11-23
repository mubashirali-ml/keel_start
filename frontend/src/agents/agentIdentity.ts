/**
 * Agent identity (ADR-0009, ADR-0019): mirrors `AGENT_PROFILES` (display name, lucide icon,
 * accent token). Messages, handoff banners and typing indicators use only this map.
 */

import { Briefcase, Globe, ListChecks, PenLine, PieChart, Scale, ShieldCheck, Tag, type LucideIcon } from "lucide-react";

import type { AgentId } from "@/api/types";

export interface AgentIdentity {
  id: AgentId;
  displayName: string;
  shortName: string;
  kind: "llm" | "deterministic";
  /** lucide icon name, as in `AgentProfile.icon`. */
  iconName: string;
  icon: LucideIcon;
  /** Design token, as in `AgentProfile.accent`. */
  accent: string;
  /** Tailwind classes using the accent token. */
  bgClass: string;
  textClass: string;
  routable: boolean;
}

export const AGENTS: Record<AgentId, AgentIdentity> = {
  manager: {
    id: "manager",
    displayName: "Manager",
    shortName: "Manager",
    kind: "llm",
    iconName: "briefcase",
    icon: Briefcase,
    accent: "agent-manager",
    bgClass: "bg-agent-manager",
    textClass: "text-agent-manager",
    routable: false,
  },
  law: {
    id: "law",
    displayName: "Law Agent",
    shortName: "Law",
    kind: "llm",
    iconName: "scale",
    icon: Scale,
    accent: "agent-law",
    bgClass: "bg-agent-law",
    textClass: "text-agent-law",
    routable: true,
  },
  name: {
    id: "name",
    displayName: "Name Agent",
    shortName: "Names",
    kind: "llm",
    iconName: "tag",
    icon: Tag,
    accent: "agent-name",
    bgClass: "bg-agent-name",
    textClass: "text-agent-name",
    routable: true,
  },
  website: {
    id: "website",
    displayName: "Website Agent",
    shortName: "Website",
    kind: "llm",
    iconName: "globe",
    icon: Globe,
    accent: "agent-website",
    bgClass: "bg-agent-website",
    textClass: "text-agent-website",
    routable: true,
  },
  qa: {
    id: "qa",
    displayName: "QA Agent",
    shortName: "QA",
    kind: "llm",
    iconName: "shield-check",
    icon: ShieldCheck,
    accent: "agent-qa",
    bgClass: "bg-agent-qa",
    textClass: "text-agent-qa",
    routable: false,
  },
  guide: {
    id: "guide",
    displayName: "Registration Guide Agent",
    shortName: "Guide",
    kind: "llm",
    iconName: "list-checks",
    icon: ListChecks,
    accent: "agent-guide",
    bgClass: "bg-agent-guide",
    textClass: "text-agent-guide",
    routable: true,
  },
  cap_table: {
    id: "cap_table",
    displayName: "Cap Table Builder",
    shortName: "Cap table",
    kind: "deterministic",
    iconName: "pie-chart",
    icon: PieChart,
    accent: "agent-cap-table",
    bgClass: "bg-agent-cap-table",
    textClass: "text-agent-cap-table",
    routable: false,
  },
  signoff: {
    id: "signoff",
    displayName: "Sign-off",
    shortName: "Sign-off",
    kind: "deterministic",
    iconName: "pen-line",
    icon: PenLine,
    accent: "agent-signoff",
    bgClass: "bg-agent-signoff",
    textClass: "text-agent-signoff",
    routable: false,
  },
};

export const AGENT_IDS = Object.keys(AGENTS) as AgentId[];

export function agentIdentity(id: AgentId | string | null | undefined): AgentIdentity {
  return (id && AGENTS[id as AgentId]) || AGENTS.manager;
}
