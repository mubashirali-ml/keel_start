/** App shell, routes and shared app hooks (ADR-0035). Features may import from here. */
export { ActingFounderProvider, useActingFounder } from "./ActingFounderContext";
export { AllowanceBanner, AppBanners, EmailVerificationBanner, TestModeBanner } from "./banners";
export { AccountMenu, CompanySwitcher, FounderSwitcher, HeaderProgress, HelpMenu, companyLabel } from "./header";
export { AppShell, AuthLayout, BareLayout, MAIN_ID, MarketingLayout, PageLoading, SkipLink } from "./layouts";
export {
  ComingSoon,
  CompanyNotFound,
  NotFoundPage,
  PageFrame,
  PlaceholderPage,
  QueryStates,
  WorkspaceViewPlaceholder,
} from "./placeholders";
export { AppRoutes, DESIGN_GALLERY_ENABLED, Titled } from "./routes";
export {
  NotAvailablePage,
  RedirectIfAuthed,
  RequireAdmin,
  RequireAuth,
  SessionLoading,
  UnauthorizedRedirect,
  loginPath,
  safeNext,
} from "./session";
export { ThemeProvider, ThemeToggle, applyTheme, readThemeChoice, useTheme, type ThemeChoice } from "./theme";
export { ProgressStrip, VIEW_META, WorkspacePage, isWorkspaceView, useWorkspace, viewFromHint } from "./Workspace";
export { AppProviders, createQueryClient } from "./providers";
