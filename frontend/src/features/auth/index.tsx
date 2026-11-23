/**
 * Placeholder pages for `features/auth` (T-042 replaces this folder; ADR-0035).
 * The login form already works against `POST /api/auth/login`, so recorded runs can log in
 * through the real form (ADR-0036): fields labelled "Email" and "Password", button "Log in".
 */
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { z } from "zod";

import { useLogin } from "@/api/hooks";
import { safeNext } from "@/app";
import { useBrandName } from "@/brand";
import { Banner, Button, EmptyState, FormField, Input, TrustNote, useZodForm } from "@/design";

const loginSchema = z.object({
  email: z.string().trim().min(1, "Enter your email address.").email("Enter a valid email address.").max(254),
  password: z.string().min(1, "Enter your password.").max(128),
});
type LoginValues = z.infer<typeof loginSchema>;

function AuthHeading({ title, description }: { title: string; description?: string }) {
  return (
    <div className="mb-6 grid gap-1.5">
      <h1 className="text-2xl font-semibold text-text">{title}</h1>
      {description && <p className="text-sm text-text-muted">{description}</p>}
    </div>
  );
}

export function LoginPage() {
  const brand = useBrandName();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const login = useLogin();
  const form = useZodForm(loginSchema, { defaultValues: { email: "", password: "" } });
  const { errors } = form.formState;
  const onSubmit = form.handleSubmit((values: LoginValues) =>
    login.mutate(values, { onSuccess: () => navigate(safeNext(params.get("next")), { replace: true }) }),
  );
  return (
    <div data-page="login">
      <AuthHeading title="Log in" description={`Welcome back to ${brand}.`} />
      <form onSubmit={onSubmit} noValidate className="grid gap-4">
        {login.isError && (
          <Banner tone="danger" title="We couldn't log you in.">
            {login.error.message}
          </Banner>
        )}
        <FormField label="Email" error={errors.email?.message} required>
          <Input type="email" autoComplete="email" {...form.register("email")} />
        </FormField>
        <FormField label="Password" error={errors.password?.message} required>
          <Input type="password" autoComplete="current-password" {...form.register("password")} />
        </FormField>
        <div className="flex justify-end">
          <Link to="/forgot-password" className="text-sm font-medium text-primary hover:underline">
            Forgot password?
          </Link>
        </div>
        <Button type="submit" size="lg" loading={login.isPending} loadingText="Logging in…">
          Log in
        </Button>
        <TrustNote kind="security">Your password is never stored in plain text and your session stays private to this browser.</TrustNote>
      </form>
      <p className="mt-6 text-center text-sm text-text-muted">
        New here?{" "}
        <Link to="/signup" className="font-medium text-primary hover:underline">
          Create an account
        </Link>
      </p>
    </div>
  );
}

function AuthPlaceholder({ title, description, page }: { title: string; description: string; page: string }) {
  return (
    <div data-page={page}>
      <AuthHeading title={title} />
      <EmptyState compact title="Nothing here yet" description={description} action={<Link to="/login" className="text-sm font-medium text-primary hover:underline">Back to log in</Link>} />
    </div>
  );
}

export function SignupPage() {
  return <AuthPlaceholder page="signup" title="Create your account" description="Sign-up is on its way." />;
}

export function ForgotPasswordPage() {
  return <AuthPlaceholder page="forgot-password" title="Reset your password" description="Password reset is on its way." />;
}

export function ResetPasswordPage() {
  return <AuthPlaceholder page="reset-password" title="Choose a new password" description="Password reset is on its way." />;
}

export function VerifyEmailPage() {
  return <AuthPlaceholder page="verify-email" title="Confirm your email" description="Email confirmation is on its way." />;
}

export function InvitePage() {
  const { token } = useParams();
  return (
    <AuthPlaceholder
      page="invite"
      title="You're invited"
      description={token ? "Accepting invitations is on its way." : "This invitation link is incomplete."}
    />
  );
}
