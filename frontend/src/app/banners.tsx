import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { onApiError } from "@/api/errors";
import { useConfig, useResendVerification, useSubscription } from "@/api/hooks";
import type { MeView } from "@/api/types";
import { Banner, Button, buttonVariants, useToast } from "@/design";
import { formatDate } from "@/lib/format";

/** "Confirm your email to sign documents" with a resend button (ADR-0035). */
export function EmailVerificationBanner({ me }: { me: MeView }) {
  const resend = useResendVerification();
  const { toast } = useToast();
  if (me.email_verified) return null;
  return (
    <Banner
      variant="page"
      tone="warning"
      title="Confirm your email to sign documents."
      action={
        <Button
          size="sm"
          variant="secondary"
          loading={resend.isPending}
          onClick={() =>
            resend.mutate(undefined, {
              onSuccess: () => toast({ tone: "success", title: "Email sent", description: `Check ${me.user.email} for the link.` }),
              onError: (e) => toast({ tone: "danger", title: "We couldn't send the email", description: e.message }),
            })
          }
        >
          Resend email
        </Button>
      }
    >
      We sent a link to {me.user.email}.
    </Banner>
  );
}

/** "Test mode: payments are simulated" when the payment gateway is fake. */
export function TestModeBanner() {
  const { data: config } = useConfig();
  if (!config?.payments_test_mode) return null;
  return (
    <Banner variant="page" tone="info" title="Test mode:">
      payments are simulated and no card is charged.
    </Banner>
  );
}

/**
 * "You've reached your plan's AI allowance" (ADR-0035): shown when the billing overview
 * says the allowance is used up, or as soon as any call fails with `usage_limit`.
 */
export function AllowanceBanner() {
  const subscription = useSubscription();
  const [hit, setHit] = useState(false);
  useEffect(() => onApiError((error) => error.code === "usage_limit" && setHit(true)), []);
  const usage = subscription.data?.usage;
  const reached = hit || (!!usage && usage.ai_messages_limit > 0 && usage.ai_messages_used >= usage.ai_messages_limit);
  if (!reached) return null;
  return (
    <Banner
      variant="page"
      tone="warning"
      title="You've reached your plan's AI allowance."
      action={
        <Link to="/app/settings/billing" className={buttonVariants({ size: "sm", variant: "secondary" })}>
          See plans
        </Link>
      }
    >
      {usage ? `It resets on ${formatDate(usage.resets_on)}.` : "Upgrade or wait until it resets."}
    </Banner>
  );
}

export function AppBanners({ me }: { me: MeView }) {
  return (
    <div data-banners="">
      <TestModeBanner />
      <EmailVerificationBanner me={me} />
      <AllowanceBanner />
    </div>
  );
}
