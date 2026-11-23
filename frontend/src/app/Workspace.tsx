import {
  CheckCircle2,
  Circle,
  CircleDot,
  FileSignature,
  Globe,
  History,
  LayoutDashboard,
  ListChecks,
  MessageSquare,
  PanelsTopLeft,
  PieChart,
  Tag,
  TriangleAlert,
  Users,
  type LucideIcon,
} from "lucide-react";
import { Suspense, createContext, lazy, useCallback, useContext, useMemo, useState, type ComponentType } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { isApiError } from "@/api/errors";
import { useCase } from "@/api/hooks";
import { WORKSPACE_VIEWS, type CaseView, type Progress as ProgressView, type StepStatus, type WorkspaceView } from "@/api/types";
import { usePageTitle } from "@/brand";
import { ErrorState, LoadingBlock, SegmentedControl, Skeleton, Tabs, TabsContent, TabsList, TabsTrigger } from "@/design";
import { cn } from "@/lib/cn";
import { STORAGE_KEYS, storage } from "@/lib/storage";
import { QUERIES, useMediaQuery } from "@/lib/useMediaQuery";

import { companyLabel } from "./header";
import { CompanyNotFound, NotFoundPage } from "./placeholders";

type ViewComponent = ComponentType<{ caseId: string }>;

/** The eight workspace views (ADR-0035); each is a feature folder's default export. */
export const VIEW_META: Record<WorkspaceView, { label: string; icon: LucideIcon; load: () => Promise<{ default: ViewComponent }> }> = {
  overview: { label: "Overview", icon: LayoutDashboard, load: () => import("@/features/overview") },
  names: { label: "Names", icon: Tag, load: () => import("@/features/names") },
  legal: { label: "Legal", icon: FileSignature, load: () => import("@/features/legal") },
  "cap-table": { label: "Cap table", icon: PieChart, load: () => import("@/features/cap-table") },
  website: { label: "Website", icon: Globe, load: () => import("@/features/website") },
  guide: { label: "Guide", icon: ListChecks, load: () => import("@/features/guide") },
  team: { label: "Team", icon: Users, load: () => import("@/features/team") },
  audit: { label: "Audit", icon: History, load: () => import("@/features/audit") },
};

const VIEWS = Object.fromEntries(WORKSPACE_VIEWS.map((v) => [v, lazy(VIEW_META[v].load)])) as unknown as Record<
  WorkspaceView,
  ViewComponent
>;
const ChatPanel = lazy(() => import("@/features/chat"));

/** `OpenView.view` hints use snake_case (`cap_table`); routes use kebab-case. */
export function viewFromHint(hint: string | null | undefined): WorkspaceView | null {
  if (!hint) return null;
  const v = hint.replace(/_/g, "-");
  return (WORKSPACE_VIEWS as readonly string[]).includes(v) ? (v as WorkspaceView) : null;
}

export function isWorkspaceView(value: string | undefined): value is WorkspaceView {
  return !!value && (WORKSPACE_VIEWS as readonly string[]).includes(value);
}

// ---------------------------------------------------------------- workspace context (for features)
interface WorkspaceContextValue {
  caseId: string;
  view: WorkspaceView;
  /** Switch the workspace to a view (e.g. on `open_view`); on phones the chat stays visible. */
  openView: (view: WorkspaceView | string) => void;
  /** Phones: show the workspace pane. */
  showWorkspace: () => void;
  isPhone: boolean;
}

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

export function useWorkspace(): WorkspaceContextValue {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) throw new Error("useWorkspace must be used inside the workspace");
  return ctx;
}

// ---------------------------------------------------------------- progress strip
const STEP_ICONS: Record<StepStatus, { icon: LucideIcon; className: string; text: string }> = {
  not_started: { icon: Circle, className: "text-text-subtle", text: "Not started" },
  in_progress: { icon: CircleDot, className: "text-info", text: "In progress" },
  done: { icon: CheckCircle2, className: "text-success", text: "Done" },
  attention: { icon: TriangleAlert, className: "text-warning", text: "Needs attention" },
};

/** The 6-step progress strip (ADR-0019); fits 390px without scrolling sideways. */
export function ProgressStrip({ progress }: { progress: ProgressView }) {
  const done = progress.steps.filter((s) => s.status === "done").length;
  return (
    <div className="grid gap-2" data-progress-strip="">
      <div className="flex items-center justify-between text-xs font-medium text-text-muted">
        <span>
          {done} of {progress.steps.length} steps done
        </span>
        <span>{progress.percent}%</span>
      </div>
      <ol className="grid grid-cols-6 gap-1.5" aria-label="Progress">
        {progress.steps.map((step, i) => {
          const s = STEP_ICONS[step.status] ?? STEP_ICONS.not_started;
          const Icon = s.icon;
          return (
            <li key={step.id} className="grid min-w-0 gap-1.5" title={step.detail || undefined}>
              <span
                aria-hidden="true"
                className={cn(
                  "h-1.5 rounded-full",
                  step.status === "done" ? "bg-success" : step.status === "attention" ? "bg-warning" : step.status === "in_progress" ? "bg-info" : "bg-surface-muted",
                )}
              />
              <span className="flex min-w-0 items-center gap-1 text-xs text-text-muted">
                <Icon size={14} aria-hidden="true" className={cn("shrink-0", s.className)} />
                <span className="hidden truncate md:inline">{step.label}</span>
                <span className="sr-only">
                  {`Step ${i + 1}: ${step.label}, ${s.text}`}
                  {step.detail ? `. ${step.detail}` : ""}
                </span>
              </span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

// ---------------------------------------------------------------- layout
type Pane = "chat" | "workspace";

function ViewFallback() {
  return <LoadingBlock lines={5} />;
}

function WorkspaceLayout({ view: caseView, current }: { view: CaseView; current: WorkspaceView }) {
  const navigate = useNavigate();
  const isPhone = useMediaQuery(QUERIES.belowLg);
  const [pane, setPaneState] = useState<Pane>(() => (storage.get(STORAGE_KEYS.mobilePane) === "workspace" ? "workspace" : "chat"));
  const setPane = useCallback((p: Pane) => {
    storage.set(STORAGE_KEYS.mobilePane, p);
    setPaneState(p);
  }, []);
  const caseId = caseView.id;
  usePageTitle(`${VIEW_META[current].label} · ${companyLabel(caseView.company_name)}`);

  const openView = useCallback(
    (target: WorkspaceView | string) => {
      const v = isWorkspaceView(target) ? target : viewFromHint(target);
      if (v) navigate(`/app/cases/${encodeURIComponent(caseId)}/${v}`);
    },
    [caseId, navigate],
  );
  const ctx = useMemo(
    () => ({ caseId, view: current, openView, showWorkspace: () => setPane("workspace"), isPhone }),
    [caseId, current, openView, setPane, isPhone],
  );
  const View = VIEWS[current];

  const chat = (
    <section aria-label="Chat" className="flex min-h-0 flex-1 flex-col" data-pane="chat">
      <Suspense fallback={<ViewFallback />}>
        <ChatPanel caseId={caseId} />
      </Suspense>
    </section>
  );

  const workspace = (
    <section aria-label="Workspace" className="flex min-h-0 min-w-0 flex-1 flex-col" data-pane="workspace">
      <Tabs value={current} onValueChange={(v) => openView(v)} className="flex min-h-0 flex-1 flex-col">
        <div className="border-b bg-surface px-4 pt-4 sm:px-6">
          <ProgressStrip progress={caseView.progress} />
          <TabsList scrollable aria-label="Workspace views" className="-mx-4 mt-3 border-b-0 px-4 sm:-mx-6 sm:px-6">
            {WORKSPACE_VIEWS.map((v) => {
              const Icon = VIEW_META[v].icon;
              return (
                <TabsTrigger key={v} value={v} data-view={v}>
                  <Icon size={16} aria-hidden="true" />
                  {VIEW_META[v].label}
                </TabsTrigger>
              );
            })}
          </TabsList>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto bg-bg px-4 py-6 sm:px-6">
          <TabsContent value={current} className="pt-0" data-view-panel={current}>
            <Suspense fallback={<ViewFallback />}>
              <View caseId={caseId} />
            </Suspense>
          </TabsContent>
        </div>
      </Tabs>
    </section>
  );

  return (
    <WorkspaceContext.Provider value={ctx}>
      {isPhone ? (
        <div className="flex h-full min-h-0 flex-col">
          <div className="border-b bg-surface px-4 py-2">
            <SegmentedControl<Pane>
              aria-label="Show"
              className="w-full"
              value={pane}
              onValueChange={setPane}
              options={[
                { value: "chat", label: <><MessageSquare size={16} aria-hidden="true" /> Chat</> },
                { value: "workspace", label: <><PanelsTopLeft size={16} aria-hidden="true" /> Workspace</> },
              ]}
            />
          </div>
          <div className="flex min-h-0 flex-1 flex-col">{pane === "chat" ? chat : workspace}</div>
        </div>
      ) : (
        <div className="grid h-full min-h-0 grid-cols-[minmax(380px,2fr)_3fr]">
          <div className="flex min-h-0 flex-col border-r bg-surface">{chat}</div>
          <div className="flex min-h-0 flex-col">{workspace}</div>
        </div>
      )}
    </WorkspaceContext.Provider>
  );
}

function WorkspaceSkeleton() {
  return (
    <div className="grid h-full min-h-0 lg:grid-cols-[minmax(380px,2fr)_3fr]" data-state="loading">
      <div role="status" aria-live="polite" className="hidden flex-col gap-4 border-r bg-surface p-4 lg:flex">
        <span className="sr-only">Loading your company…</span>
        {Array.from({ length: 4 }, (_, i) => (
          <div key={i} className="flex gap-3">
            <Skeleton width={36} height={36} rounded="full" />
            <div className="grid flex-1 gap-2">
              <Skeleton height={14} width="30%" />
              <Skeleton height={48} />
            </div>
          </div>
        ))}
      </div>
      <div className="grid content-start gap-4 p-4 sm:p-6">
        <Skeleton height={8} />
        <Skeleton height={36} />
        <Skeleton height={160} />
        <Skeleton height={96} />
      </div>
    </div>
  );
}

/** `/app/cases/:caseId/:view?` */
export function WorkspacePage() {
  const { caseId = "", view } = useParams();
  const current: WorkspaceView | null = view === undefined ? "overview" : isWorkspaceView(view) ? view : null;
  const query = useCase(caseId);
  if (!current) return <NotFoundPage />;
  if (query.isPending) return <WorkspaceSkeleton />;
  if (query.isError) {
    if (isApiError(query.error) && query.error.isNotFound) return <CompanyNotFound />;
    return (
      <div className="mx-auto w-full max-w-xl px-4 py-16">
        <ErrorState
          title="We couldn't open this company"
          error={query.error}
          onRetry={() => query.refetch()}
          retrying={query.isFetching}
        />
      </div>
    );
  }
  return <WorkspaceLayout view={query.data} current={current} />;
}
