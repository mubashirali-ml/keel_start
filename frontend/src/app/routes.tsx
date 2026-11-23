import { lazy, Suspense, type ComponentType, type ReactNode } from "react";
import { Outlet, Route, Routes, useParams } from "react-router-dom";

import { useConfig, useMe } from "@/api/hooks";
import { ADMIN_SECTIONS, SETTINGS_SECTIONS } from "@/api/types";
import { usePageTitle } from "@/brand";

import { AppShell, AuthLayout, BareLayout, MarketingLayout, PageLoading } from "./layouts";
import { NotFoundPage } from "./placeholders";
import { RedirectIfAuthed, RequireAdmin, RequireAuth, UnauthorizedRedirect } from "./session";
import { WorkspacePage } from "./Workspace";

/** Pages are code-split per feature folder (marketing and auth chunks stay small, ADR-0035). */
function page<M>(load: () => Promise<M>, name: keyof M & string) {
  return lazy(async () => ({ default: (await load())[name] as unknown as ComponentType }));
}

const marketing = () => import("@/features/marketing");
const auth = () => import("@/features/auth");
const onboarding = () => import("@/features/onboarding");
const settings = () => import("@/features/settings");
const admin = () => import("@/features/admin");

const LandingPage = page(marketing, "LandingPage");
const PricingPage = page(marketing, "PricingPage");
const TermsPage = page(marketing, "TermsPage");
const PrivacyPage = page(marketing, "PrivacyPage");
const DisclaimerPage = page(marketing, "DisclaimerPage");
const SecurityPage = page(marketing, "SecurityPage");
const LoginPage = page(auth, "LoginPage");
const SignupPage = page(auth, "SignupPage");
const ForgotPasswordPage = page(auth, "ForgotPasswordPage");
const ResetPasswordPage = page(auth, "ResetPasswordPage");
const VerifyEmailPage = page(auth, "VerifyEmailPage");
const InvitePage = page(auth, "InvitePage");
const CompaniesPage = page(onboarding, "CompaniesPage");
const OnboardingPage = page(onboarding, "OnboardingPage");
const SettingsPage = page(settings, "SettingsPage");
const TestCheckoutPage = page(settings, "TestCheckoutPage");
const AdminPage = page(admin, "AdminPage");
/** `/design` exists in development builds and in recorded-run builds (VITE_DESIGN_GALLERY=1). */
export const DESIGN_GALLERY_ENABLED = import.meta.env.DEV || import.meta.env.VITE_DESIGN_GALLERY === "1";
// Production builds drop the gallery chunk entirely.
const DesignGallery = DESIGN_GALLERY_ENABLED ? lazy(() => import("@/design/gallery/DesignGallery")) : () => null;

/** Sets the page title (`{page} · {brand}`; `null` = the landing title) for a route. */
export function Titled({ title, children }: { title: string | null; children: ReactNode }) {
  usePageTitle(title);
  return <>{children}</>;
}

function Root() {
  return (
    <>
      <UnauthorizedRedirect />
      <Outlet />
    </>
  );
}

function SectionGuard({ sections, children }: { sections: readonly string[]; children: ReactNode }) {
  const { section } = useParams();
  if (section !== undefined && !sections.includes(section)) return <NotFoundPage />;
  return <>{children}</>;
}

function TestCheckoutGuard({ children }: { children: ReactNode }) {
  const { data: config } = useConfig();
  if (!config?.payments_test_mode) return <NotFoundPage />;
  return <>{children}</>;
}

function Shell() {
  return <RequireAuth>{(me) => <AppShell me={me} />}</RequireAuth>;
}

/** Inside the App shell (the session is loaded): admins only. */
function AdminArea() {
  const me = useMe().data;
  if (!me) return null;
  return (
    <RequireAdmin me={me}>
      <SectionGuard sections={ADMIN_SECTIONS}>
        <Titled title="Admin">
          <AdminPage />
        </Titled>
      </SectionGuard>
    </RequireAdmin>
  );
}

/** Every route of ADR-0035, each inside its layout. */
export function AppRoutes() {
  return (
    <Routes>
      <Route element={<Root />}>
        <Route element={<MarketingLayout />}>
          <Route index element={<Titled title={null}><LandingPage /></Titled>} />
          <Route path="pricing" element={<Titled title="Pricing"><PricingPage /></Titled>} />
          <Route path="terms" element={<Titled title="Terms of service"><TermsPage /></Titled>} />
          <Route path="privacy" element={<Titled title="Privacy"><PrivacyPage /></Titled>} />
          <Route path="disclaimer" element={<Titled title="Disclaimer"><DisclaimerPage /></Titled>} />
          <Route path="security" element={<Titled title="Security"><SecurityPage /></Titled>} />
        </Route>

        <Route element={<AuthLayout />}>
          <Route path="login" element={<Titled title="Log in"><RedirectIfAuthed><LoginPage /></RedirectIfAuthed></Titled>} />
          <Route path="signup" element={<Titled title="Sign up"><RedirectIfAuthed><SignupPage /></RedirectIfAuthed></Titled>} />
          <Route
            path="forgot-password"
            element={<Titled title="Forgot password"><RedirectIfAuthed><ForgotPasswordPage /></RedirectIfAuthed></Titled>}
          />
          <Route path="reset-password" element={<Titled title="Reset password"><ResetPasswordPage /></Titled>} />
          <Route path="verify-email" element={<Titled title="Confirm your email"><VerifyEmailPage /></Titled>} />
          <Route path="invite/:token" element={<Titled title="Invitation"><InvitePage /></Titled>} />
        </Route>

        <Route path="app" element={<Shell />}>
          <Route index element={<Titled title="Your companies"><CompaniesPage /></Titled>} />
          <Route path="onboarding" element={<Titled title="Start a company"><OnboardingPage /></Titled>} />
          <Route path="cases/:caseId/:view?" element={<WorkspacePage />} />
          <Route
            path="settings/:section?"
            element={
              <SectionGuard sections={SETTINGS_SECTIONS}>
                <Titled title="Settings"><SettingsPage /></Titled>
              </SectionGuard>
            }
          />
          <Route
            path="billing/test-checkout"
            element={<TestCheckoutGuard><Titled title="Test checkout"><TestCheckoutPage /></Titled></TestCheckoutGuard>}
          />
          <Route path="*" element={<NotFoundPage />} />
        </Route>

        <Route path="admin" element={<Shell />}>
          <Route path=":section?" element={<AdminArea />} />
        </Route>

        {DESIGN_GALLERY_ENABLED && (
          <Route
            path="design"
            element={
              <BareLayout>
                <Titled title="Design system">
                  <Suspense fallback={<PageLoading />}>
                    <DesignGallery />
                  </Suspense>
                </Titled>
              </BareLayout>
            }
          />
        )}

        <Route element={<MarketingLayout />}>
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Route>
    </Routes>
  );
}
