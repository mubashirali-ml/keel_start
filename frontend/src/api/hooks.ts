/**
 * React Query hooks over the client (ADR-0019, ADR-0035, ADR-0038). Mutations invalidate
 * the company and the lists they affect. The client already retries GETs on network
 * errors, so React Query itself does not retry.
 */

import { useMutation, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";

import * as api from "./client";
import { DEFAULT_CONFIG } from "./defaults";
import { isApiError } from "./errors";
import {
  FINISHED_JOB_STATUSES,
  type BillingInterval,
  type EditRequest,
  type JobRecord,
  type JobStatus,
  type MeView,
  type PlanId,
  type PublicConfig,
  type SignRequest,
} from "./types";

export const JOB_POLL_MS = 1500;

/** Query keys, one place (features invalidate with these). */
export const qk = {
  config: ["config"] as const,
  agents: ["agents"] as const,
  me: ["me"] as const,
  plans: ["plans"] as const,
  subscription: ["subscription"] as const,
  cases: ["cases"] as const,
  case: (id: string) => ["case", id] as const,
  messages: (id: string) => ["case", id, "messages"] as const,
  names: (id: string) => ["case", id, "names"] as const,
  guide: (id: string) => ["case", id, "guide"] as const,
  jobs: (id: string) => ["case", id, "jobs"] as const,
  job: (id: string, jobId: string) => ["case", id, "jobs", jobId] as const,
  capTable: (id: string) => ["case", id, "cap-table"] as const,
  documents: (id: string) => ["case", id, "documents"] as const,
  document: (id: string, docId: string) => ["case", id, "documents", docId] as const,
  audit: (id: string) => ["case", id, "audit"] as const,
  website: (id: string) => ["case", id, "website"] as const,
  members: (id: string) => ["case", id, "members"] as const,
  invites: (id: string) => ["case", id, "invites"] as const,
  invitePreview: (token: string) => ["invite", token] as const,
  admin: (section: string, params?: unknown) => ["admin", section, params ?? null] as const,
};

// ---------------------------------------------------------------- session and config
/** The public config; compiled defaults while `/api/config` is missing or unreachable. */
export function useConfig() {
  return useQuery<PublicConfig>({
    queryKey: qk.config,
    queryFn: async () => {
      try {
        return { ...DEFAULT_CONFIG, ...(await api.getConfig()) };
      } catch {
        return DEFAULT_CONFIG;
      }
    },
    placeholderData: DEFAULT_CONFIG,
    staleTime: 5 * 60_000,
  });
}

/** The logged-in user, or `null` when logged out (401; also 404 until the auth routes exist). */
export function useMe() {
  return useQuery<MeView | null>({
    queryKey: qk.me,
    queryFn: async () => {
      try {
        const me = await api.getMe();
        api.rememberCsrfToken(me.csrf_token);
        return me;
      } catch (error) {
        if (isApiError(error) && (error.status === 401 || error.status === 404)) return null;
        throw error;
      }
    },
    staleTime: 60_000,
  });
}

function setMe(qc: QueryClient, me: MeView | null) {
  if (me) api.rememberCsrfToken(me.csrf_token);
  qc.setQueryData(qk.me, me);
}

export function useAgents() {
  return useQuery({ queryKey: qk.agents, queryFn: api.listAgents, staleTime: Infinity });
}

// ---------------------------------------------------------------- auth
export function useLogin() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: api.login, onSuccess: (me) => setMe(qc, me) });
}

export function useSignup() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: api.signup, onSuccess: (me) => setMe(qc, me) });
}

export function useLogout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.logout,
    onSettled: () => {
      api.rememberCsrfToken(null);
      qc.clear();
      qc.setQueryData(qk.me, null);
    },
  });
}

export function useVerifyEmail() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: api.verifyEmail, onSuccess: (me) => setMe(qc, me) });
}

export function useResendVerification() {
  return useMutation({ mutationFn: api.resendVerification });
}

export function useForgotPassword() {
  return useMutation({ mutationFn: api.forgotPassword });
}

export function useResetPassword() {
  return useMutation({ mutationFn: (v: { token: string; password: string }) => api.resetPassword(v.token, v.password) });
}

// ---------------------------------------------------------------- account
export function useUpdateAccount() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: api.updateAccount, onSuccess: (me) => setMe(qc, me) });
}

export function useChangePassword() {
  return useMutation({ mutationFn: api.changePassword });
}

export function useExport() {
  return useMutation({ mutationFn: api.exportAccount });
}

export function useDeleteAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.deleteAccount,
    onSuccess: () => {
      qc.clear();
      qc.setQueryData(qk.me, null);
    },
  });
}

// ---------------------------------------------------------------- team
export function useMembers(caseId: string) {
  return useQuery({ queryKey: qk.members(caseId), queryFn: () => api.listMembers(caseId) });
}

export function useInvites(caseId: string, enabled = true) {
  return useQuery({ queryKey: qk.invites(caseId), queryFn: () => api.listInvites(caseId), enabled });
}

export function useCreateInvite(caseId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { email: string; founder_id?: string | null }) => api.createInvite(caseId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.invites(caseId) }),
  });
}

export function useRevokeInvite(caseId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (inviteId: string) => api.revokeInvite(caseId, inviteId),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.invites(caseId) }),
  });
}

export function useRemoveMember(caseId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) => api.removeMember(caseId, userId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.members(caseId) });
      qc.invalidateQueries({ queryKey: qk.me });
    },
  });
}

export function useInvitePreview(token: string) {
  return useQuery({ queryKey: qk.invitePreview(token), queryFn: () => api.getInvitePreview(token) });
}

export function useAcceptInvite() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.acceptInvite,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.me });
      qc.invalidateQueries({ queryKey: qk.cases });
    },
  });
}

// ---------------------------------------------------------------- billing (ADR-0038)
export function usePlans() {
  return useQuery({ queryKey: qk.plans, queryFn: api.listPlans, staleTime: 5 * 60_000 });
}

/** The billing overview: subscription, plan and usage (`BillingOverview`). */
export function useSubscription(enabled = true) {
  return useQuery({ queryKey: qk.subscription, queryFn: api.getSubscription, enabled });
}

export function useCheckout() {
  return useMutation({ mutationFn: api.startCheckout });
}

export function usePortal() {
  return useMutation({ mutationFn: api.openPortal });
}

/** In-app "Switch plan" between paid plans / intervals (ADR-0038). */
export function useChangePlan() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { plan: PlanId; interval: BillingInterval }) => api.changePlan(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.subscription });
      qc.invalidateQueries({ queryKey: qk.me });
    },
  });
}

export function useCompleteTestCheckout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.completeTestCheckout,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.subscription });
      qc.invalidateQueries({ queryKey: qk.me });
    },
  });
}

// ---------------------------------------------------------------- cases
export function useCases(enabled = true) {
  return useQuery({ queryKey: qk.cases, queryFn: api.listCases, enabled });
}

export function useCase(caseId: string | undefined) {
  return useQuery({ queryKey: qk.case(caseId ?? ""), queryFn: () => api.getCase(caseId!), enabled: !!caseId });
}

export function useCreateCase() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.createCase,
    onSuccess: (view) => {
      qc.setQueryData(qk.case(view.id), view);
      qc.invalidateQueries({ queryKey: qk.cases });
      qc.invalidateQueries({ queryKey: qk.me });
    },
  });
}

export function useDeleteCase() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.deleteCase,
    onSuccess: (_data, caseId) => {
      qc.removeQueries({ queryKey: qk.case(caseId) });
      qc.invalidateQueries({ queryKey: qk.cases });
      qc.invalidateQueries({ queryKey: qk.me });
    },
  });
}

export function useMessages(caseId: string) {
  return useQuery({ queryKey: qk.messages(caseId), queryFn: () => api.listMessages(caseId) });
}

export function usePostMessage(caseId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (text: string) => api.postMessage(caseId, text),
    onSuccess: (result) => {
      qc.setQueryData(qk.case(caseId), result.case);
      qc.invalidateQueries({ queryKey: qk.messages(caseId) });
      if (result.jobs.length) qc.invalidateQueries({ queryKey: qk.jobs(caseId) });
    },
  });
}

export function useNames(caseId: string) {
  return useQuery({ queryKey: qk.names(caseId), queryFn: () => api.listNames(caseId) });
}

export function useChooseName(caseId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string; domain?: string | null }) => api.chooseName(caseId, body),
    onSuccess: (view) => {
      qc.setQueryData(qk.case(caseId), view);
      qc.invalidateQueries({ queryKey: qk.names(caseId) });
      qc.invalidateQueries({ queryKey: qk.messages(caseId) });
      qc.invalidateQueries({ queryKey: qk.cases });
    },
  });
}

export function useRecheckNames(caseId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.recheckNames(caseId),
    onSuccess: (names) => qc.setQueryData(qk.names(caseId), names),
  });
}

export function useGuide(caseId: string) {
  return useQuery({ queryKey: qk.guide(caseId), queryFn: () => api.getGuide(caseId) });
}

export function useSetGuideItem(caseId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { itemId: string; done: boolean }) => api.setGuideItem(caseId, v.itemId, v.done),
    onSuccess: (guide) => {
      qc.setQueryData(qk.guide(caseId), guide);
      qc.invalidateQueries({ queryKey: qk.case(caseId) });
    },
  });
}

export function useJobs(caseId: string) {
  return useQuery({ queryKey: qk.jobs(caseId), queryFn: () => api.listJobs(caseId) });
}

export function isJobFinished(status: JobStatus | undefined): boolean {
  return !!status && FINISHED_JOB_STATUSES.includes(status);
}

/** One job, polled every 1.5 s until it has finished (ADR-0035). */
export function useJob(caseId: string, jobId: string | null | undefined) {
  const qc = useQueryClient();
  return useQuery<JobRecord>({
    queryKey: qk.job(caseId, jobId ?? ""),
    queryFn: async () => {
      const job = await api.getJob(caseId, jobId!);
      if (isJobFinished(job.status)) {
        qc.invalidateQueries({ queryKey: qk.case(caseId) });
        if (job.kind.startsWith("website.")) qc.invalidateQueries({ queryKey: qk.website(caseId) });
      }
      return job;
    },
    enabled: !!jobId,
    refetchInterval: (query) => (isJobFinished(query.state.data?.status) ? false : JOB_POLL_MS),
  });
}

// ---------------------------------------------------------------- legal
export function useCapTable(caseId: string) {
  return useQuery({ queryKey: qk.capTable(caseId), queryFn: () => api.getCapTable(caseId) });
}

export function useDocuments(caseId: string) {
  return useQuery({ queryKey: qk.documents(caseId), queryFn: () => api.listDocuments(caseId) });
}

export function useDocument(caseId: string, docId: string) {
  return useQuery({ queryKey: qk.document(caseId, docId), queryFn: () => api.getDocument(caseId, docId) });
}

function invalidateLegal(qc: QueryClient, caseId: string) {
  qc.invalidateQueries({ queryKey: qk.documents(caseId) });
  qc.invalidateQueries({ queryKey: qk.audit(caseId) });
  qc.invalidateQueries({ queryKey: qk.case(caseId) });
  qc.invalidateQueries({ queryKey: qk.messages(caseId) });
}

export function useGenerateDocuments(caseId: string) {
  const qc = useQueryClient();
  return useMutation({ mutationFn: () => api.generateDocuments(caseId), onSuccess: () => invalidateLegal(qc, caseId) });
}

export function useSignDocument(caseId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { docId: string; body: SignRequest }) => api.signDocument(caseId, v.docId, v.body),
    onSuccess: () => invalidateLegal(qc, caseId),
  });
}

export function useEditDocument(caseId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { docId: string; body: EditRequest }) => api.editDocument(caseId, v.docId, v.body),
    onSuccess: () => invalidateLegal(qc, caseId),
  });
}

export function useAudit(caseId: string) {
  return useQuery({ queryKey: qk.audit(caseId), queryFn: () => api.getAudit(caseId) });
}

// ---------------------------------------------------------------- website
export function useWebsite(caseId: string) {
  return useQuery({ queryKey: qk.website(caseId), queryFn: () => api.getWebsite(caseId) });
}

export function useBuildWebsite(caseId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (changeRequest?: string | null) => api.buildWebsite(caseId, changeRequest),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.jobs(caseId) });
      qc.invalidateQueries({ queryKey: qk.case(caseId) });
    },
  });
}

export function useDeployWebsite(caseId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (overrideQa: boolean = false) => api.deployWebsite(caseId, overrideQa),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.jobs(caseId) });
      qc.invalidateQueries({ queryKey: qk.case(caseId) });
    },
  });
}

// ---------------------------------------------------------------- admin
export function useAdminUsers(params: { query?: string; page?: number; plan?: PlanId | null } = {}) {
  return useQuery({ queryKey: qk.admin("users", params), queryFn: () => api.adminUsers(params) });
}

export function useAdminCases(params: { query?: string; page?: number } = {}) {
  return useQuery({ queryKey: qk.admin("companies", params), queryFn: () => api.adminCases(params) });
}

export function useAdminUsage(params: { month?: string } = {}) {
  return useQuery({ queryKey: qk.admin("usage", params), queryFn: () => api.adminUsage(params) });
}

export function useAdminJobs(params: { status?: JobStatus | null; page?: number } = {}) {
  return useQuery({ queryKey: qk.admin("jobs", params), queryFn: () => api.adminJobs(params) });
}

export function useAdminEmails(params: { status?: string | null; page?: number } = {}) {
  return useQuery({ queryKey: qk.admin("emails", params), queryFn: () => api.adminEmails(params) });
}

export function useAdminSystem() {
  return useQuery({ queryKey: qk.admin("system"), queryFn: api.adminSystem });
}

export function useAdminRetryJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.adminRetryJob,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "jobs"] }),
  });
}
