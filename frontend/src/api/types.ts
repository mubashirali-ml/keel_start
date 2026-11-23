/**
 * API types mirroring the backend views field for field (ADR-0008/0009/0013/0014/0015/0016,
 * ADR-0026, ADR-0028, ADR-0030/0038, ADR-0031, ADR-0032, ADR-0034). snake_case is kept;
 * decimals arrive as strings; dates are ISO strings ("2026-12-01"), datetimes ISO 8601.
 */

export type ISODate = string;
export type ISODateTime = string;
export type Decimal = string;

// ---------------------------------------------------------------- agents and messages (ADR-0009)
export type AgentId = "manager" | "law" | "name" | "website" | "qa" | "guide" | "cap_table" | "signoff";

export interface AgentProfile {
  id: AgentId;
  display_name: string;
  short_name: string;
  kind: "llm" | "deterministic";
  icon: string;
  accent: string;
  routable: boolean;
}

export type MessageRole = "founder" | "agent" | "system";
export type MessageKind =
  | "text"
  | "handoff"
  | "notice"
  | "validation"
  | "name_options"
  | "documents_ready"
  | "cap_table_ready"
  | "site_preview"
  | "qa_report"
  | "deploy_status"
  | "guide_ready";

export interface SuggestedReply {
  label: string;
  text: string;
}

export interface ChatMessage {
  id: string | null;
  case_id: string | null;
  seq: number | null;
  role: MessageRole;
  agent: AgentId | null;
  founder_id: string | null;
  kind: MessageKind;
  content: string;
  payload: Record<string, unknown>;
  suggested_replies: SuggestedReply[];
  created_at: ISODateTime | null;
}

/** `OpenView.view` values (ADR-0009): a UI hint returned with chat turns. */
export type OpenViewHint = "overview" | "names" | "legal" | "cap_table" | "website" | "guide" | "audit";

// ---------------------------------------------------------------- facts (ADR-0008, ADR-0013)
export type EntityType = "LLC" | "Delaware C-Corp";

export interface Founder {
  id: string;
  name: string;
  email: string;
  equity_percent: Decimal;
  vesting_months: number | null;
  cliff_months: number | null;
}

export interface WebsiteRequirements {
  pages: string[];
  services: string[];
  about: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  contact_address: string | null;
  extra_content: string[];
  style_notes: string | null;
}

export interface CaseFacts {
  business_description: string | null;
  founders: Founder[];
  entity_type: EntityType | null;
  state: string | null;
  incorporation_date: ISODate | null;
  name_preferences: string[];
  company_name: string | null;
  website: WebsiteRequirements;
}

export interface ValidationIssue {
  code: string;
  field: string;
  message: string;
  founder_id: string | null;
}

export interface LegalIssue {
  code: string;
  severity: "info" | "warning";
  message: string;
}

// ---------------------------------------------------------------- names (ADR-0011)
export type DomainStatus = "available" | "taken" | "unknown";

export interface DomainCheck {
  domain: string;
  status: DomainStatus;
  source: string;
  checked_at: ISODateTime;
  detail: string | null;
}

export interface StateNameCheck {
  state: string;
  status: "check_manually";
  search_url: string;
  office_url: string;
}

export interface NameCandidate {
  name: string;
  rationale: string;
  domains: DomainCheck[];
  state_check: StateNameCheck | null;
  trademark_search_url: string;
}

// ---------------------------------------------------------------- cap table (ADR-0013)
export interface VestingEvent {
  month: number;
  date: ISODate;
  vested_this_event: number;
  cumulative_vested: number;
}

export interface CapTableRow {
  founder_id: string;
  name: string;
  email: string;
  equity_percent: Decimal;
  shares: number;
  vesting_months: number;
  cliff_months: number;
  schedule: VestingEvent[];
}

export interface CapTable {
  entity_type: EntityType;
  unit_label: "shares" | "units";
  authorized: number;
  vesting_start: ISODate;
  rows: CapTableRow[];
  total_issued: number;
}

// ---------------------------------------------------------------- documents (ADR-0014, ADR-0031)
export type DocumentKind = "ip_assignment" | "bylaws_summary" | "operating_agreement_summary" | "election_83b";
export type DocumentStatus = "awaiting_signatures" | "executed";

export interface Signature {
  founder_id: string;
  version: number;
  signed_at: ISODateTime;
  user_id: string | null;
  typed_name: string;
  consent_version: string;
  content_sha256: string;
  ip: string | null;
  user_agent: string | null;
  acted_by_user_id: string | null;
}

export interface Document {
  id: string;
  case_id: string;
  kind: DocumentKind;
  title: string;
  founder_id: string | null;
  version: number;
  content: string;
  status: DocumentStatus;
  required_signers: string[];
  signatures: Signature[];
  created_at: ISODateTime;
  updated_at: ISODateTime;
}

export type AuditAction =
  | "created"
  | "signed"
  | "edited"
  | "signatures_invalidated"
  | "executed"
  | "reopened"
  | "regenerated"
  | "rejected_stale"
  | "rejected_not_signer"
  | "rejected_already_signed"
  | "legal_complete"
  | "facts_locked"
  | "name_chosen"
  | "checklist_updated"
  | "site_built"
  | "site_deployed"
  | "deploy_override"
  | "pdf_downloaded"
  | "member_joined"
  | "invite_sent"
  | "plan_changed";

export interface AuditEntry {
  id: number | null;
  case_id: string;
  document_id: string | null;
  actor: string;
  action: AuditAction;
  from_version: number | null;
  to_version: number | null;
  detail: Record<string, unknown>;
  at: ISODateTime;
}

export interface SignRequest {
  version: number;
  content_sha256: string;
  typed_name: string;
  consent: true;
}

export interface EditRequest extends SignRequest {
  content: string;
}

export interface DocumentsOutcome {
  documents: Document[];
  messages: ChatMessage[];
}

export interface EditOutcome {
  document: Document;
  invalidated: string[];
}

// ---------------------------------------------------------------- website (ADR-0015)
export interface SiteSection {
  heading: string;
  body: string;
  items: string[];
}
export interface SitePage {
  slug: string;
  title: string;
  nav_label: string;
  sections: SiteSection[];
}
export interface SiteContact {
  email: string | null;
  phone: string | null;
  address: string | null;
}
export interface SiteFounder {
  name: string;
  bio: string;
}
export interface SiteContent {
  company_name: string;
  tagline: string;
  pages: SitePage[];
  contact: SiteContact;
  founders: SiteFounder[];
  footer_note: string;
}
export interface SiteFile {
  path: string;
  content: string;
  content_type: string;
}
export interface SiteBundle {
  files: SiteFile[];
}
export type QaCheckId =
  | "pages_present"
  | "content_present"
  | "company_name"
  | "contact_details"
  | "internal_links"
  | "image_alt"
  | "headings"
  | "html_structure"
  | "contrast"
  | "requirements_review";
export interface QaIssue {
  check: QaCheckId;
  severity: "error" | "warning";
  page: string | null;
  message: string;
}
export interface QaCheckResult {
  check: QaCheckId;
  label: string;
  passed: boolean;
  issues: QaIssue[];
}
export interface QaReport {
  passed: boolean;
  round: number;
  checks: QaCheckResult[];
  checked_at: ISODateTime;
}
export type SiteBuildStatus = "qa_passed" | "qa_failed" | "deployed" | "deploy_failed" | "deploy_not_configured";
export interface SiteBuild {
  id: string;
  case_id: string;
  version: number;
  content: SiteContent;
  bundle: SiteBundle;
  qa_reports: QaReport[];
  qa_passed: boolean;
  fix_rounds: number;
  status: SiteBuildStatus;
  deploy_url: string | null;
  deploy_message: string | null;
  override_by: string | null;
  created_at: ISODateTime;
  updated_at: ISODateTime;
}

// ---------------------------------------------------------------- registration guide (ADR-0016)
export interface GuideLink {
  label: string;
  url: string;
}
export type GuideCategory = "name" | "formation" | "agent" | "ein" | "agreement" | "83b" | "domain" | "ongoing";
export interface GuideStep {
  id: string;
  category: GuideCategory;
  title: string;
  detail: string;
  links: GuideLink[];
  fee: string | null;
  due: ISODate | null;
  optional: boolean;
}
export interface RegistrationGuide {
  state: string;
  state_name: string;
  entity_type: EntityType;
  full_guide: boolean;
  steps: GuideStep[];
  last_reviewed: ISODate;
  sources: GuideLink[];
  disclaimer: string;
}
export interface GuideView {
  guide: RegistrationGuide;
  done: Record<string, boolean>;
  done_count: number;
  total: number;
}

// ---------------------------------------------------------------- jobs (ADR-0028)
export type JobStatus = "queued" | "running" | "succeeded" | "failed" | "cancelled";
export type JobKind = "website.build" | "website.deploy" | "email.send" | "reminders.sweep" | (string & {});

export interface JobRecord {
  id: string;
  kind: JobKind;
  status: JobStatus;
  case_id: string | null;
  user_id: string | null;
  payload: Record<string, unknown>;
  result: Record<string, unknown> | null;
  error: string | null;
  attempts: number;
  max_attempts: number;
  run_at: ISODateTime;
  created_at: ISODateTime;
  updated_at: ISODateTime;
  finished_at: ISODateTime | null;
}

export const FINISHED_JOB_STATUSES: readonly JobStatus[] = ["succeeded", "failed", "cancelled"];

// ---------------------------------------------------------------- accounts (ADR-0026)
export interface User {
  id: string;
  email: string;
  full_name: string;
  email_verified_at: ISODateTime | null;
  is_admin: boolean;
  created_at: ISODateTime;
}

export type MemberRole = "owner" | "member";

export interface Invite {
  id: string;
  case_id: string;
  email: string;
  founder_id: string | null;
  invited_by: string;
  created_at: ISODateTime;
  expires_at: ISODateTime;
  accepted_at: ISODateTime | null;
  revoked_at: ISODateTime | null;
}

export interface MemberView {
  user_id: string;
  full_name: string;
  email: string;
  role: MemberRole;
  founder_id: string | null;
  founder_name: string | null;
  joined_at: ISODateTime;
}

export interface InvitePreview {
  company_name: string | null;
  inviter_name: string;
  email_hint: string;
  founder_name: string | null;
  expired: boolean;
}

// ---------------------------------------------------------------- billing (ADR-0030, ADR-0038)
export type PlanId = "free" | "launch" | "team";
export type BillingInterval = "month" | "year";
export type Feature = "documents" | "esign" | "signed_pdf" | "website_deploy";
export type SupportLevel = "basic" | "standard" | "priority";
export type SubscriptionStatus = "none" | "active" | "trialing" | "past_due" | "canceled" | "incomplete";

export interface Plan {
  id: PlanId;
  rank: number;
  name: string;
  tagline: string;
  price_month_cents: number;
  price_year_cents: number;
  yearly_available: boolean;
  features: Feature[];
  max_companies: number;
  llm_calls_per_month: number;
  support: SupportLevel;
  support_label: string;
  highlights: string[];
}

export interface Subscription {
  user_id: string;
  plan: PlanId;
  interval: BillingInterval | null;
  status: SubscriptionStatus;
  current_period_end: ISODateTime | null;
  cancel_at_period_end: boolean;
  provider_customer_id: string | null;
  provider_subscription_id: string | null;
}

export interface UsageSummary {
  ai_messages_used: number;
  ai_messages_limit: number;
  resets_on: ISODate;
  companies_used: number;
  companies_limit: number;
}

export interface BillingOverview {
  subscription: Subscription;
  plan: Plan;
  usage: UsageSummary;
  can_switch_plan: boolean;
}

export interface PriceCheck {
  plan: PlanId;
  interval: BillingInterval;
  price_id: string | null;
  expected_cents: number;
  provider_cents: number | null;
  ok: boolean;
  problem: string | null;
}

export interface UrlResult {
  url: string;
}

// ---------------------------------------------------------------- case views (ADR-0017, ADR-0032)
export type StepId = "facts" | "name" | "legal" | "cap_table" | "website" | "registration";
export type StepStatus = "not_started" | "in_progress" | "done" | "attention";

export interface StepProgress {
  id: StepId;
  label: string;
  status: StepStatus;
  detail: string;
}

export interface Progress {
  steps: StepProgress[];
  percent: number;
}

export interface CaseView {
  id: string;
  created_at: ISODateTime;
  updated_at: ISODateTime;
  facts: CaseFacts;
  facts_locked: boolean;
  active_agent: AgentId;
  company_name: string | null;
  chosen_domain: string | null;
  validation_issues: ValidationIssue[];
  missing_facts: string[];
  deadline_83b: ISODate | null;
  days_until_83b: number | null;
  progress: Progress;
  legal_issues: LegalIssue[];
  my_role: MemberRole | null;
  my_founder_id: string | null;
  plan: PlanId;
  active_jobs: JobRecord[];
}

export interface CaseSummary {
  id: string;
  company_name: string | null;
  created_at: ISODateTime;
  updated_at: ISODateTime;
  percent: number;
}

export interface PostMessageResult {
  messages: ChatMessage[];
  case: CaseView;
  open_view: string | null;
  jobs: JobRecord[];
}

export interface SiteJobOutcome {
  job: JobRecord;
  build: SiteBuild | null;
}

export interface MeView {
  user: User;
  plan: PlanId;
  subscription: Subscription;
  email_verified: boolean;
  companies: CaseSummary[];
  csrf_token: string;
}

export interface PublicConfig {
  brand_name: string;
  demo_mode: boolean;
  payments_test_mode: boolean;
  hosting_configured: boolean;
  plans: Plan[];
  esign_consent_text: string;
  esign_consent_version: string;
  support_email: string | null;
  yearly_enabled: boolean;
}

export interface HealthStatus {
  status: string;
}

export interface ReadyStatus {
  status: string;
  checks: Record<string, unknown>;
}

// ---------------------------------------------------------------- admin (ADR-0034, ADR-0038)
export interface AdminPage<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
}

export interface AdminUserRow {
  user_id: string;
  email: string;
  full_name: string;
  created_at: ISODateTime;
  email_verified: boolean;
  plan: PlanId;
  support: SupportLevel;
  companies: number;
  last_seen_at: ISODateTime | null;
}

export interface AdminCaseRow {
  case_id: string;
  company_name: string | null;
  members: number;
  created_at: ISODateTime;
  facts_locked: boolean;
  documents_executed: boolean;
  site_published: boolean;
  plan: PlanId;
}

export interface AdminUsageRow {
  user_id: string;
  email: string;
  plan: PlanId;
  calls: number;
  input_tokens: number;
  output_tokens: number;
  limit: number;
}

export interface OutboxEmailRow {
  id: string;
  to_masked: string;
  template: string;
  status: string;
  error: string | null;
  created_at: ISODateTime;
  sent_at: ISODateTime | null;
}

export interface SystemInfo {
  llm_provider: string;
  llm_models: Record<string, string>;
  domain_checker: string;
  hosting_provider: string;
  hosting_configured: boolean;
  email_provider: string;
  payments_mode: string;
  schema_current: boolean | null;
  last_worker_heartbeat: ISODateTime | null;
  price_checks: PriceCheck[];
}

// ---------------------------------------------------------------- errors (ADR-0017 envelope)
export interface ErrorEnvelope {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
    request_id?: string;
  };
}

// ---------------------------------------------------------------- routes (ADR-0035)
/** Workspace views of `/app/cases/:caseId/:view?`. */
export const WORKSPACE_VIEWS = ["overview", "names", "legal", "cap-table", "website", "guide", "team", "audit"] as const;
export type WorkspaceView = (typeof WORKSPACE_VIEWS)[number];

export const SETTINGS_SECTIONS = ["profile", "security", "billing", "privacy"] as const;
export type SettingsSection = (typeof SETTINGS_SECTIONS)[number];

export const ADMIN_SECTIONS = ["users", "companies", "usage", "jobs", "emails", "system"] as const;
export type AdminSection = (typeof ADMIN_SECTIONS)[number];
