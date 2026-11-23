/**
 * `/design`: every shared component in all variants and states, in the current theme, plus
 * the logo in light, dark and one-colour variants (ADR-0019, ADR-0041). Development and
 * recorded-run builds only.
 */
import { Bell, Download, Pencil, Plus, Settings, Trash2 } from "lucide-react";
import { useState, type ReactNode } from "react";
import { z } from "zod";

import { AGENT_IDS, AgentAvatar, AgentLabel } from "@/agents";
import { ApiError } from "@/api/errors";
import { ThemeToggle } from "@/app/theme";
import { Logo, LogoMark, TAGLINE, useBrandName, useDisclaimer } from "@/brand";
import { cn } from "@/lib/cn";

import {
  Avatar,
  Badge,
  Banner,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
  Checkbox,
  ConfirmDialog,
  Countdown,
  Dialog,
  DialogClose,
  DialogContent,
  DialogTrigger,
  EmptyState,
  ErrorState,
  FormField,
  IconButton,
  Input,
  LoadingBlock,
  Markdown,
  Menu,
  MenuContent,
  MenuItem,
  MenuLabel,
  MenuSeparator,
  MenuTrigger,
  PlanGate,
  Popover,
  PopoverContent,
  PopoverTrigger,
  Progress,
  RadioGroup,
  SegmentedControl,
  Select,
  Skeleton,
  StatusBadge,
  Switch,
  Table,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  Textarea,
  Tooltip,
  TrustNote,
  useToast,
  useZodForm,
} from "..";

export const GALLERY_SECTIONS = [
  "Logo",
  "Colors",
  "Typography",
  "Button",
  "IconButton",
  "Input",
  "Textarea",
  "Select",
  "Checkbox",
  "Switch",
  "RadioGroup",
  "FormField",
  "SegmentedControl",
  "Card",
  "Tabs",
  "Badge",
  "StatusBadge",
  "Dialog",
  "ConfirmDialog",
  "Toast",
  "Popover",
  "Menu",
  "Tooltip",
  "Banner",
  "TrustNote",
  "PlanGate",
  "EmptyState",
  "ErrorState",
  "Skeleton",
  "Progress",
  "Avatar",
  "AgentAvatar",
  "Table",
  "Markdown",
  "Countdown",
] as const;

function Section({ name, description, children }: { name: (typeof GALLERY_SECTIONS)[number]; description?: string; children: ReactNode }) {
  return (
    <section id={`gallery-${name}`} aria-labelledby={`gallery-${name}-title`} className="scroll-mt-20 rounded-lg border bg-surface p-5 shadow-sm" data-gallery-section={name}>
      <h2 id={`gallery-${name}-title`} className="text-lg font-semibold text-text">
        {name}
      </h2>
      {description && <p className="mt-1 text-sm text-text-muted">{description}</p>}
      <div className="mt-4 grid gap-4">{children}</div>
    </section>
  );
}

function Row({ label, children, className }: { label?: string; children: ReactNode; className?: string }) {
  return (
    <div className="grid gap-2">
      {label && <p className="text-xs font-medium uppercase tracking-wide text-text-subtle">{label}</p>}
      <div className={cn("flex flex-wrap items-center gap-3", className)}>{children}</div>
    </div>
  );
}

const SWATCHES: { name: string; className: string; fg?: string }[] = [
  { name: "bg", className: "bg-bg" },
  { name: "surface", className: "bg-surface" },
  { name: "surface-raised", className: "bg-surface-raised" },
  { name: "surface-muted", className: "bg-surface-muted" },
  { name: "border", className: "bg-border" },
  { name: "border-strong", className: "bg-border-strong" },
  { name: "text", className: "bg-text", fg: "text-bg" },
  { name: "text-muted", className: "bg-text-muted", fg: "text-bg" },
  { name: "primary", className: "bg-primary", fg: "text-primary-fg" },
  { name: "primary-soft", className: "bg-primary-soft", fg: "text-primary" },
  { name: "success", className: "bg-success", fg: "text-success-fg" },
  { name: "warning", className: "bg-warning", fg: "text-warning-fg" },
  { name: "danger", className: "bg-danger", fg: "text-danger-fg" },
  { name: "info", className: "bg-info", fg: "text-info-fg" },
  { name: "focus-ring", className: "bg-focus-ring", fg: "text-bg" },
];

const ROWS = [
  { id: "f1", name: "Alice Chen", percent: "60", shares: "6,000,000", vesting: "48 months, 12-month cliff" },
  { id: "f2", name: "Bob Diaz", percent: "40", shares: "4,000,000", vesting: "48 months, 12-month cliff" },
];

const demoSchema = z.object({
  email: z.string().trim().min(1, "Enter an email address.").email("Enter a valid email address."),
  company: z.string().trim().min(2, "Use at least 2 characters.").max(120, "Use at most 120 characters."),
});

function FormFieldDemo() {
  const form = useZodForm(demoSchema, { defaultValues: { email: "not-an-email", company: "" } });
  const { errors } = form.formState;
  return (
    <form noValidate onSubmit={form.handleSubmit(() => undefined)} className="grid max-w-md gap-4">
      <FormField label="Work email" hint="We'll send the sign-in link here." error={errors.email?.message} required>
        <Input type="email" {...form.register("email")} />
      </FormField>
      <FormField label="Company name" error={errors.company?.message}>
        <Input {...form.register("company")} />
      </FormField>
      <Button type="submit" className="justify-self-start">
        Check fields
      </Button>
    </form>
  );
}

const featureGate = new ApiError({
  code: "plan_required",
  status: 402,
  message: "Electronic signatures are included in the Launch and Team plans.",
  details: { feature: "esign", required_plan: "launch" },
  requestId: "req-demo-0001",
});
const companyGate = new ApiError({
  code: "plan_required",
  status: 402,
  message: "Your plan includes 3 companies. Upgrade to Team to add more.",
  details: { required_plan: "team" },
});
const sampleError = new ApiError({
  code: "temporarily_unavailable",
  status: 503,
  message: "We're temporarily unavailable. Please try again in a minute.",
  requestId: "req-7f3a9c21",
});

export default function DesignGallery() {
  const brand = useBrandName();
  const disclaimer = useDisclaimer();
  const { toast } = useToast();
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [checked, setChecked] = useState(true);
  const [pane, setPane] = useState<"chat" | "workspace">("chat");
  const [interval, setInterval] = useState("month");
  const today = new Date(2026, 10, 23);

  return (
    <div className="mx-auto grid max-w-6xl gap-6 px-4 py-8 sm:px-6" data-page="design">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div className="grid gap-1">
          <Logo size="lg" />
          <h1 className="text-2xl font-semibold text-text">Design system</h1>
          <p className="text-sm text-text-muted">Tokens and shared components, in the current theme. Use the theme control to switch.</p>
        </div>
        <ThemeToggle />
      </header>
      <nav aria-label="Components" className="flex flex-wrap gap-2">
        {GALLERY_SECTIONS.map((s) => (
          <a key={s} href={`#gallery-${s}`} className="rounded-full border bg-surface px-3 py-1 text-xs font-medium text-text-muted hover:text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring">
            {s}
          </a>
        ))}
      </nav>
      <main id="main-content" tabIndex={-1} className="grid gap-6 outline-none">
        <Section name="Logo" description="Sailboat mark with the word mark; legible at 16 px and 32 px; one-colour variant uses currentColor.">
          <div className="grid gap-4 md:grid-cols-3">
            <div className="light grid gap-3 rounded-md border bg-bg p-4 text-text" data-logo-variant="light">
              <p className="text-xs font-medium text-text-muted">Light</p>
              <Logo size="lg" />
              <div className="flex items-end gap-3 text-primary">
                <LogoMark size={16} title={`${brand} mark at 16 px`} />
                <LogoMark size={32} title={`${brand} mark at 32 px`} />
                <LogoMark size={56} />
              </div>
            </div>
            <div className="dark grid gap-3 rounded-md border bg-bg p-4 text-text" data-logo-variant="dark">
              <p className="text-xs font-medium text-text-muted">Dark</p>
              <Logo size="lg" />
              <div className="flex items-end gap-3 text-primary">
                <LogoMark size={16} />
                <LogoMark size={32} />
                <LogoMark size={56} />
              </div>
            </div>
            <div className="grid gap-3 rounded-md bg-primary p-4 text-primary-fg" data-logo-variant="one-colour">
              <p className="text-xs font-medium">One colour (currentColor)</p>
              <Logo size="lg" tone="current" />
              <div className="flex items-end gap-3">
                <LogoMark size={16} />
                <LogoMark size={32} />
                <LogoMark size={56} />
              </div>
            </div>
          </div>
          <p className="text-sm text-text-muted">
            Tagline: {TAGLINE}. Disclaimer: {disclaimer}
          </p>
        </Section>

        <Section name="Colors" description="Every color is a token; components never use raw colors. Ratios are checked for WCAG AA in tests.">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            {SWATCHES.map((s) => (
              <div key={s.name} className="overflow-hidden rounded-md border">
                <div className={cn("flex h-14 items-end p-2 text-xs font-medium", s.className, s.fg ?? "text-text")}>Aa</div>
                <p className="bg-surface px-2 py-1.5 text-xs text-text-muted">{s.name}</p>
              </div>
            ))}
          </div>
          <Row label="Agent accents">
            {AGENT_IDS.map((id) => (
              <AgentLabel key={id} agent={id} />
            ))}
          </Row>
        </Section>

        <Section name="Typography" description="Inter Variable; scale xs 12/16 to 3xl 30/36.">
          <div className="grid gap-2">
            <p className="text-3xl font-semibold">3xl Launch your company</p>
            <p className="text-2xl font-semibold">2xl Founding documents</p>
            <p className="text-xl font-semibold">xl Cap table</p>
            <p className="text-lg">lg Your agents are ready</p>
            <p className="text-base">base Body text for reading at length.</p>
            <p className="text-sm text-text-muted">sm Secondary text</p>
            <p className="text-xs text-text-subtle">xs Hints and captions</p>
          </div>
        </Section>

        <Section name="Button">
          <Row label="Variants">
            <Button>Primary</Button>
            <Button variant="secondary">Secondary</Button>
            <Button variant="ghost">Ghost</Button>
            <Button variant="danger">Danger</Button>
            <Button variant="link">Link</Button>
          </Row>
          <Row label="Sizes">
            <Button size="sm">Small</Button>
            <Button size="md">Medium</Button>
            <Button size="lg">Large</Button>
          </Row>
          <Row label="States">
            <Button leftIcon={<Plus size={16} aria-hidden="true" />}>With icon</Button>
            <Button loading loadingText="Saving…">
              Save
            </Button>
            <Button disabled>Disabled</Button>
            <Button variant="secondary" loading>
              Loading
            </Button>
          </Row>
        </Section>

        <Section name="IconButton" description="Icon-only buttons always carry an aria-label.">
          <Row>
            <IconButton aria-label="Edit" icon={<Pencil size={18} />} />
            <IconButton aria-label="Download" variant="secondary" icon={<Download size={18} />} />
            <IconButton aria-label="Add" variant="primary" icon={<Plus size={18} />} />
            <IconButton aria-label="Settings" size="sm" icon={<Settings size={16} />} />
            <IconButton aria-label="Delete (disabled)" disabled icon={<Trash2 size={18} />} />
          </Row>
        </Section>

        <Section name="Input">
          <div className="grid max-w-xl gap-3 sm:grid-cols-2">
            <Input aria-label="Default input" placeholder="Placeholder" />
            <Input aria-label="Filled input" defaultValue="Acme Bakery Software" />
            <Input aria-label="Invalid input" invalid defaultValue="not-an-email" />
            <Input aria-label="Disabled input" disabled defaultValue="Disabled" />
          </div>
        </Section>

        <Section name="Textarea">
          <div className="grid max-w-xl gap-3 sm:grid-cols-2">
            <Textarea aria-label="Default textarea" placeholder="Tell the Manager about your business…" />
            <Textarea aria-label="Invalid textarea" invalid defaultValue="Too long" />
          </div>
        </Section>

        <Section name="Select">
          <div className="grid max-w-xl gap-3 sm:grid-cols-2">
            <Select
              aria-label="State"
              placeholder="Choose a state"
              options={[
                { value: "DE", label: "Delaware" },
                { value: "WY", label: "Wyoming" },
                { value: "CA", label: "California" },
              ]}
            />
            <Select aria-label="Entity type" defaultValue="LLC" options={[{ value: "LLC", label: "LLC" }, { value: "Delaware C-Corp", label: "Delaware C-Corp" }]} />
            <Select aria-label="Disabled select" disabled options={[{ value: "x", label: "Disabled" }]} />
            <Select aria-label="Invalid select" invalid options={[{ value: "x", label: "Option" }]} />
          </div>
        </Section>

        <Section name="Checkbox">
          <div className="grid gap-3">
            <Checkbox label="I agree to sign electronically" description="Your typed name is your signature." checked={checked} onCheckedChange={(v) => setChecked(v === true)} />
            <Checkbox label="Unchecked" />
            <Checkbox label="Indeterminate" checked="indeterminate" />
            <Checkbox label="Disabled" disabled />
          </div>
        </Section>

        <Section name="Switch">
          <div className="grid max-w-md gap-4">
            <Switch label="Email me about deadlines" description="83(b) and filing reminders." defaultChecked />
            <Switch label="Off" />
            <Switch label="Disabled" disabled />
          </div>
        </Section>

        <Section name="RadioGroup">
          <div className="grid gap-4 md:grid-cols-2">
            <RadioGroup
              aria-label="Billing interval (list)"
              value={interval}
              onValueChange={setInterval}
              options={[
                { value: "month", label: "Monthly", description: "$29 a month" },
                { value: "year", label: "Yearly", description: "$290 a year, two months free" },
                { value: "disabled", label: "Unavailable", disabled: true },
              ]}
            />
            <RadioGroup
              aria-label="Billing interval (cards)"
              layout="cards"
              defaultValue="year"
              options={[
                { value: "month", label: "Monthly", description: "$29 / month" },
                { value: "year", label: "Yearly", description: "$290 / year" },
              ]}
            />
          </div>
        </Section>

        <Section name="FormField" description="react-hook-form + zod: errors are linked with aria-describedby and announced.">
          <FormFieldDemo />
        </Section>

        <Section name="SegmentedControl" description="Phones switch between Chat and Workspace.">
          <SegmentedControl
            aria-label="Show"
            value={pane}
            onValueChange={setPane}
            options={[
              { value: "chat", label: "Chat" },
              { value: "workspace", label: "Workspace" },
            ]}
          />
        </Section>

        <Section name="Card">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>IP assignment</CardTitle>
                <CardDescription>Alice Chen assigns her work to the company.</CardDescription>
              </CardHeader>
              <CardContent>
                <StatusBadge kind="document" status="awaiting_signatures" />
              </CardContent>
              <CardFooter>
                <Button size="sm">Review and sign</Button>
                <Button size="sm" variant="ghost">
                  Download
                </Button>
              </CardFooter>
            </Card>
            <Card raised>
              <CardHeader>
                <CardTitle>Raised card</CardTitle>
                <CardDescription>For popovers and highlighted content.</CardDescription>
              </CardHeader>
            </Card>
          </div>
        </Section>

        <Section name="Tabs" description="Arrow keys move between tabs.">
          <Tabs defaultValue="overview">
            <TabsList scrollable aria-label="Example tabs">
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="legal">Legal</TabsTrigger>
              <TabsTrigger value="website">Website</TabsTrigger>
              <TabsTrigger value="disabled" disabled>
                Disabled
              </TabsTrigger>
            </TabsList>
            <TabsContent value="overview">Overview content.</TabsContent>
            <TabsContent value="legal">Legal content.</TabsContent>
            <TabsContent value="website">Website content.</TabsContent>
          </Tabs>
        </Section>

        <Section name="Badge" description="Always an icon plus text.">
          <Row>
            <Badge>Neutral</Badge>
            <Badge tone="success">Success</Badge>
            <Badge tone="warning">Warning</Badge>
            <Badge tone="danger">Danger</Badge>
            <Badge tone="info">Info</Badge>
            <Badge tone="primary">Launch plan</Badge>
            <Badge tone="info" size="sm" icon={Bell}>
              Small
            </Badge>
          </Row>
        </Section>

        <Section name="StatusBadge">
          <Row label="Steps">
            <StatusBadge kind="step" status="not_started" />
            <StatusBadge kind="step" status="in_progress" />
            <StatusBadge kind="step" status="done" />
            <StatusBadge kind="step" status="attention" />
          </Row>
          <Row label="Documents and domains">
            <StatusBadge kind="document" status="awaiting_signatures" />
            <StatusBadge kind="document" status="executed" />
            <StatusBadge kind="domain" status="available" />
            <StatusBadge kind="domain" status="taken" />
            <StatusBadge kind="domain" status="unknown" />
          </Row>
          <Row label="Website and jobs">
            <StatusBadge kind="site" status="qa_passed" />
            <StatusBadge kind="site" status="qa_failed" />
            <StatusBadge kind="site" status="deployed" />
            <StatusBadge kind="site" status="deploy_failed" />
            <StatusBadge kind="site" status="deploy_not_configured" />
            <StatusBadge kind="job" status="queued" />
            <StatusBadge kind="job" status="running" />
            <StatusBadge kind="job" status="failed" />
          </Row>
        </Section>

        <Section name="Dialog" description="Focus stays inside; Escape closes; focus returns to the trigger.">
          <Dialog>
            <DialogTrigger asChild>
              <Button variant="secondary" className="justify-self-start">
                Open dialog
              </Button>
            </DialogTrigger>
            <DialogContent
              title="Invite a co-founder"
              description="They'll get an email with a link to join this company."
              footer={
                <>
                  <DialogClose asChild>
                    <Button variant="secondary">Cancel</Button>
                  </DialogClose>
                  <Button>Send invite</Button>
                </>
              }
            >
              <FormField label="Email">
                <Input type="email" placeholder="bob@example.com" />
              </FormField>
            </DialogContent>
          </Dialog>
        </Section>

        <Section name="ConfirmDialog">
          <Button variant="danger" className="justify-self-start" onClick={() => setConfirmOpen(true)}>
            Delete company
          </Button>
          <ConfirmDialog
            open={confirmOpen}
            onOpenChange={setConfirmOpen}
            tone="danger"
            title="Delete this company?"
            description="Its documents, chat and website are deleted for every member. This can't be undone."
            confirmLabel="Delete company"
            onConfirm={() => new Promise((resolve) => setTimeout(resolve, 600))}
          />
        </Section>

        <Section name="Toast" description="Announced politely to screen readers.">
          <Row>
            <Button variant="secondary" onClick={() => toast({ tone: "success", title: "Document signed", description: "Bob will get an email." })}>
              Success toast
            </Button>
            <Button variant="secondary" onClick={() => toast({ tone: "info", title: "Website build started" })}>
              Info toast
            </Button>
            <Button variant="secondary" onClick={() => toast({ tone: "danger", title: "We couldn't save that", description: "Please try again." })}>
              Error toast
            </Button>
          </Row>
        </Section>

        <Section name="Popover">
          <Popover>
            <PopoverTrigger asChild>
              <Button variant="secondary" className="justify-self-start">
                What is an 83(b) election?
              </Button>
            </PopoverTrigger>
            <PopoverContent aria-label="83(b) election">
              <p className="font-semibold">83(b) election</p>
              <p className="mt-1 text-text-muted">A letter to the IRS within 30 days of getting shares that vest. Your Guide lists the steps.</p>
            </PopoverContent>
          </Popover>
        </Section>

        <Section name="Menu">
          <Menu>
            <MenuTrigger asChild>
              <Button variant="secondary" className="justify-self-start">
                Open menu
              </Button>
            </MenuTrigger>
            <MenuContent align="start">
              <MenuLabel>Document</MenuLabel>
              <MenuItem icon={<Download size={16} />}>Download PDF</MenuItem>
              <MenuItem icon={<Pencil size={16} />}>Edit</MenuItem>
              <MenuSeparator />
              <MenuItem danger icon={<Trash2 size={16} />}>
                Delete
              </MenuItem>
            </MenuContent>
          </Menu>
        </Section>

        <Section name="Tooltip">
          <Tooltip content="Downloads a signed PDF">
            <Button variant="secondary" className="justify-self-start">
              Hover or focus me
            </Button>
          </Tooltip>
        </Section>

        <Section name="Banner">
          <Banner tone="warning" title="Confirm your email to sign documents." action={<Button size="sm" variant="secondary">Resend email</Button>}>
            We sent a link to alice@example.com.
          </Banner>
          <Banner tone="info" title="Test mode:">
            payments are simulated and no card is charged.
          </Banner>
          <Banner tone="success" title="All documents signed." onDismiss={() => undefined}>
            You can download the signed PDFs.
          </Banner>
          <Banner tone="danger" title="Publishing failed.">
            The host didn't respond. Try again in a minute.
          </Banner>
        </Section>

        <Section name="TrustNote">
          <TrustNote kind="security">Payments are handled by Stripe. We never see your card number.</TrustNote>
          <TrustNote kind="disclaimer">{disclaimer}</TrustNote>
          <TrustNote kind="info">Co-founders join free on every plan.</TrustNote>
        </Section>

        <Section name="PlanGate" description="Wraps an action whose call can return plan_required.">
          <PlanGate error={featureGate}>
            <Button className="justify-self-start">Sign document</Button>
          </PlanGate>
          <PlanGate error={companyGate}>
            <Button variant="secondary" className="justify-self-start">
              New company
            </Button>
          </PlanGate>
          <PlanGate error={null}>
            <Button variant="secondary" className="justify-self-start">
              Allowed action (no prompt)
            </Button>
          </PlanGate>
        </Section>

        <Section name="EmptyState">
          <EmptyState title="No documents yet" description="Lock your company facts and the Law Agent drafts them." action={<Button size="sm">Draft documents</Button>} />
          <EmptyState compact title="Compact empty state" />
        </Section>

        <Section name="ErrorState" description="Friendly text, a reference id and a recovery action; never raw JSON.">
          <ErrorState error={sampleError} onRetry={() => undefined} actions={<Button variant="ghost">Contact support</Button>} />
          <ErrorState compact title="We couldn't load the cap table" message="Check your connection and try again." onRetry={() => undefined} />
        </Section>

        <Section name="Skeleton" description="Fixed sizes so content never shifts.">
          <div className="grid max-w-md gap-2">
            <Skeleton height={20} width="50%" />
            <Skeleton height={14} />
            <Skeleton height={14} width="80%" />
            <div className="flex items-center gap-3">
              <Skeleton width={36} height={36} rounded="full" />
              <Skeleton height={14} width="40%" />
            </div>
          </div>
          <LoadingBlock lines={2} label="Loading example…" />
        </Section>

        <Section name="Progress">
          <div className="grid max-w-md gap-4">
            <Progress value={0} label="Not started" showValue />
            <Progress value={50} label="Company progress" showValue />
            <Progress value={100} label="Complete" showValue size="sm" />
          </div>
        </Section>

        <Section name="Avatar">
          <Row>
            <Avatar name="Alice Chen" size="sm" />
            <Avatar name="Bob Diaz" />
            <Avatar name="Carmen" size="lg" />
          </Row>
        </Section>

        <Section name="AgentAvatar" description="Each agent's icon in its accent colour, with its name as the accessible name.">
          <Row>
            {AGENT_IDS.map((id) => (
              <AgentAvatar key={id} agent={id} size="lg" />
            ))}
          </Row>
        </Section>

        <Section name="Table" description="Stacks into cards below 640px.">
          <Table
            caption="Cap table"
            captionVisible
            rowKey={(r) => r.id}
            rows={ROWS}
            columns={[
              { key: "name", header: "Founder", cell: (r) => <span className="font-medium">{r.name}</span> },
              { key: "percent", header: "Equity", align: "right", cell: (r) => `${r.percent}%` },
              { key: "shares", header: "Units", align: "right", cell: (r) => r.shares },
              { key: "vesting", header: "Vesting", cell: (r) => r.vesting },
            ]}
          />
          <Table caption="Empty table" rowKey={(r: { id: string }) => r.id} rows={[]} columns={[]} empty={<EmptyState compact title="No rows yet" />} />
        </Section>

        <Section name="Markdown">
          <Markdown>
            {"**Next step:** review your documents.\n\n- IP assignment\n- Operating agreement summary\n\nRead the [Wyoming filing guide](https://sos.wyo.gov).\n\n> Filing usually takes one to three business days.\n\nYour documents use `Acme Bakery Software LLC`:\n\n```\nArticles of Organization\nRegistered agent consent\n```"}
          </Markdown>
        </Section>

        <Section name="Countdown">
          <Row>
            <Countdown date="2026-12-31" today={today} label="83(b) due" />
            <Countdown date="2026-11-28" today={today} label="83(b) due" />
            <Countdown date="2026-11-23" today={today} />
            <Countdown date="2026-11-20" today={today} />
          </Row>
        </Section>
      </main>
    </div>
  );
}
