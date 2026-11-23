/**
 * Placeholder for `features/admin` (T-045 replaces this folder; ADR-0035).
 * Named export: AdminPage (`users`, `companies`, `usage`, `jobs`, `emails`, `system`).
 */
import { NavLink, useParams } from "react-router-dom";

import { ADMIN_SECTIONS, type AdminSection } from "@/api/types";
import { ComingSoon, PageFrame } from "@/app";
import { focusRing } from "@/design";
import { cn } from "@/lib/cn";

const LABELS: Record<AdminSection, string> = {
  users: "Users",
  companies: "Companies",
  usage: "Usage",
  jobs: "Jobs",
  emails: "Emails",
  system: "System",
};

export function AdminPage() {
  const { section = "users" } = useParams();
  const current = (ADMIN_SECTIONS as readonly string[]).includes(section) ? (section as AdminSection) : "users";
  return (
    <PageFrame title="Admin" description="Metadata only: no chat text, documents or website content." width="lg">
      <nav aria-label="Admin" className="mb-6 flex gap-1 overflow-x-auto border-b">
        {ADMIN_SECTIONS.map((s) => (
          <NavLink
            key={s}
            to={`/admin/${s}`}
            className={() =>
              cn(
                "-mb-px shrink-0 border-b-2 px-3 py-2 text-sm font-medium",
                s === current ? "border-primary text-primary" : "border-transparent text-text-muted hover:text-text",
                focusRing,
              )
            }
          >
            {LABELS[s]}
          </NavLink>
        ))}
      </nav>
      <ComingSoon title={`${LABELS[current]} is on its way`} description="This admin view is being built." />
    </PageFrame>
  );
}
