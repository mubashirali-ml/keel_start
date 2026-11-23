/**
 * "Contact support" (ADR-0038, wording ADR-0042): a mailto: to `PublicConfig.support_email`
 * whose subject starts with `[{Plan name}]` and carries the request id of the last error,
 * so the owner can spot plan and context at a glance. No reply time is promised anywhere.
 */

import type { ApiError } from "./errors";

export function supportMailto(email: string, planName: string, lastError: ApiError | null): string {
  const ref = lastError?.requestId ? ` (ref ${lastError.requestId})` : "";
  const subject = `[${planName}] Help request${ref}`;
  const lines = ["Hi, I need help with:", "", ""];
  if (lastError?.requestId) {
    lines.push("---", `Request id: ${lastError.requestId}`, `Last error: ${lastError.message}`);
  }
  const body = lines.join("\n");
  return `mailto:${email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
}
