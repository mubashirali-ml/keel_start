import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { z } from "zod";

import { ApiError } from "@/api/errors";
import { setViewport } from "@/test/media";
import { renderWithProviders } from "@/test/renderWithProviders";

import {
  Badge,
  Button,
  Checkbox,
  ConfirmDialog,
  Dialog,
  DialogClose,
  DialogContent,
  DialogTrigger,
  ErrorState,
  FormField,
  IconButton,
  Input,
  PlanGate,
  RadioGroup,
  SegmentedControl,
  StatusBadge,
  Switch,
  Table,
  Tabs,
  TabsList,
  TabsTrigger,
  Countdown,
  planGateCopy,
  useToast,
  useZodForm,
} from "..";

describe("Dialog", () => {
  function Example() {
    return (
      <Dialog>
        <DialogTrigger asChild>
          <Button>Open</Button>
        </DialogTrigger>
        <DialogContent title="Invite a co-founder" footer={<DialogClose asChild><Button variant="secondary">Cancel</Button></DialogClose>}>
          <Input aria-label="Email" />
        </DialogContent>
      </Dialog>
    );
  }

  it("traps focus inside, closes on Escape and returns focus to the trigger", async () => {
    const user = userEvent.setup();
    renderWithProviders(<Example />);
    const trigger = screen.getByRole("button", { name: "Open" });
    await user.click(trigger);
    const dialog = await screen.findByRole("dialog", { name: "Invite a co-founder" });
    // Tab many times: focus never leaves the dialog.
    for (let i = 0; i < 6; i++) {
      await user.tab();
      expect(dialog.contains(document.activeElement)).toBe(true);
    }
    await user.tab({ shift: true });
    expect(dialog.contains(document.activeElement)).toBe(true);
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(trigger).toHaveFocus();
  });

  it("ConfirmDialog runs the action and closes", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn(async () => undefined);
    function Confirm() {
      const [open, setOpen] = useState(true);
      return <ConfirmDialog open={open} onOpenChange={setOpen} title="Delete this company?" confirmLabel="Delete" tone="danger" onConfirm={onConfirm} />;
    }
    renderWithProviders(<Confirm />);
    await user.click(await screen.findByRole("button", { name: "Delete" }));
    expect(onConfirm).toHaveBeenCalledOnce();
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });
});

describe("Toast", () => {
  it("announces politely to screen readers", async () => {
    const user = userEvent.setup();
    function Trigger() {
      const { toast } = useToast();
      return <Button onClick={() => toast({ title: "Document signed", tone: "success" })}>Notify</Button>;
    }
    renderWithProviders(<Trigger />);
    await user.click(screen.getByRole("button", { name: "Notify" }));
    await waitFor(() => {
      const live = Array.from(document.querySelectorAll('[aria-live="polite"]')).filter((el) => el.textContent?.includes("Document signed"));
      expect(live.length).toBeGreaterThan(0);
    });
    expect(document.querySelector('[aria-live="assertive"]')).toBeNull();
    expect(screen.getAllByText("Document signed").length).toBeGreaterThan(0);
  });
});

describe("Table", () => {
  const rows = [
    { id: "f1", name: "Alice Chen", pct: "60%" },
    { id: "f2", name: "Bob Diaz", pct: "40%" },
  ];
  const columns = [
    { key: "name", header: "Founder", cell: (r: (typeof rows)[number]) => r.name },
    { key: "pct", header: "Equity", cell: (r: (typeof rows)[number]) => r.pct },
  ];

  it("renders a real table at 640px and wider", () => {
    setViewport(1024);
    renderWithProviders(<Table caption="Cap table" rows={rows} columns={columns} rowKey={(r) => r.id} />);
    const table = screen.getByRole("table", { name: "Cap table" });
    expect(within(table).getAllByRole("columnheader").map((c) => c.textContent)).toEqual(["Founder", "Equity"]);
  });

  it("stacks into labelled cards below 640px", () => {
    setViewport(390);
    renderWithProviders(<Table caption="Cap table" rows={rows} columns={columns} rowKey={(r) => r.id} />);
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    const list = screen.getByRole("list", { name: "Cap table" });
    const cards = within(list).getAllByRole("listitem");
    expect(cards).toHaveLength(2);
    expect(within(cards[0]).getByText("Founder")).toBeInTheDocument();
    expect(within(cards[0]).getByText("Alice Chen")).toBeInTheDocument();
  });
});

describe("IconButton", () => {
  it("requires an aria-label by type and exposes it as the accessible name", () => {
    // @ts-expect-error - an IconButton without aria-label must not compile (ADR-0019).
    const missing = <IconButton icon={<span>x</span>} />;
    expect(missing).toBeTruthy();
    render(<IconButton aria-label="Download PDF" icon={<span>x</span>} />);
    expect(screen.getByRole("button", { name: "Download PDF" })).toBeInTheDocument();
  });
});

describe("FormField with zod", () => {
  const schema = z.object({ email: z.string().email("Enter a valid email address.") });
  function Form() {
    const form = useZodForm(schema, { defaultValues: { email: "" } });
    return (
      <form onSubmit={form.handleSubmit(() => undefined)} noValidate>
        <FormField label="Email" hint="We'll never share it." error={form.formState.errors.email?.message}>
          <Input {...form.register("email")} />
        </FormField>
        <Button type="submit">Save</Button>
      </form>
    );
  }

  it("shows the zod error, linked to the field and announced", async () => {
    const user = userEvent.setup();
    renderWithProviders(<Form />);
    const input = screen.getByLabelText("Email");
    expect(input).not.toHaveAttribute("aria-invalid");
    await user.type(input, "nope");
    await user.click(screen.getByRole("button", { name: "Save" }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Enter a valid email address.");
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input).toHaveAccessibleDescription(/We'll never share it\. Enter a valid email address\./);
  });
});

describe("PlanGate", () => {
  const feature = new ApiError({
    code: "plan_required",
    status: 402,
    message: "Electronic signatures are included in the Launch and Team plans.",
    details: { feature: "esign", required_plan: "launch" },
  });

  it("names every plan with the feature for a feature gate", () => {
    renderWithProviders(
      <PlanGate error={feature}>
        <Button>Sign</Button>
      </PlanGate>,
    );
    expect(screen.getByRole("button", { name: "Sign" })).toBeInTheDocument();
    expect(screen.getByText("Available on Launch and Team")).toBeInTheDocument();
    expect(screen.getByText(feature.message)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "See plans" })).toHaveAttribute("href", "/pricing");
  });

  it("names the next plan for the company limit", () => {
    const limit = new ApiError({ code: "plan_required", status: 402, message: "Your plan includes 3 companies.", details: { required_plan: "team" } });
    renderWithProviders(<PlanGate error={limit} />);
    expect(screen.getByText("Upgrade to Team for more companies")).toBeInTheDocument();
  });

  it("falls back to Launch when the plan is missing or unknown", () => {
    const bare = new ApiError({ code: "plan_required", status: 402, message: "Upgrade to continue.", details: { feature: "documents" } });
    expect(planGateCopy(bare).plan.id).toBe("launch");
    expect(planGateCopy(bare).heading).toBe("Available on Launch and Team");
    const unknown = new ApiError({ code: "plan_required", status: 402, message: "x", details: { required_plan: "enterprise" } });
    expect(planGateCopy(unknown).heading).toBe("Upgrade to Launch for more companies");
  });

  it("renders only the action for other errors", () => {
    renderWithProviders(
      <PlanGate error={new ApiError({ code: "conflict", status: 409, message: "x" })}>
        <Button>Sign</Button>
      </PlanGate>,
    );
    expect(screen.queryByText(/Available on/)).not.toBeInTheDocument();
  });
});

describe("focus-visible ring", () => {
  it("every interactive component carries the focus-ring classes", () => {
    renderWithProviders(
      <div>
        <Button>Primary</Button>
        <IconButton aria-label="Edit" icon={<span />} />
        <Checkbox aria-label="Agree" />
        <Switch aria-label="Notify" />
        <RadioGroup aria-label="Interval" options={[{ value: "m", label: "Monthly" }]} />
        <SegmentedControl aria-label="Pane" value="a" onValueChange={() => undefined} options={[{ value: "a", label: "A" }]} />
        <Tabs defaultValue="a">
          <TabsList aria-label="Tabs">
            <TabsTrigger value="a">A</TabsTrigger>
          </TabsList>
        </Tabs>
        <Input aria-label="Name" />
      </div>,
    );
    const focusables = [
      screen.getByRole("button", { name: "Primary" }),
      screen.getByRole("button", { name: "Edit" }),
      screen.getByRole("checkbox", { name: "Agree" }),
      screen.getByRole("switch", { name: "Notify" }),
      screen.getByRole("radio", { name: "Monthly" }),
      screen.getByRole("radio", { name: "A" }),
      screen.getByRole("tab", { name: "A" }),
      screen.getByRole("textbox", { name: "Name" }),
    ];
    for (const el of focusables) expect(el.className, el.outerHTML).toMatch(/focus-visible:ring-2/);
    for (const el of focusables.slice(0, -1)) expect(el.className).toMatch(/focus-visible:ring-focus-ring/);
  });

  it("no source removes the focus outline without putting a ring in its place", () => {
    const sources = import.meta.glob("/src/**/*.tsx", { query: "?raw", import: "default", eager: true }) as Record<string, string>;
    const offenders: string[] = [];
    for (const [path, text] of Object.entries(sources)) {
      if (/\.test\.tsx$/.test(path)) continue;
      text.split("\n").forEach((line, i) => {
        if (line.includes("focus-visible:outline-none") && !line.includes("focus-visible:ring-")) offenders.push(`${path}:${i + 1}`);
      });
    }
    expect(offenders).toEqual([]);
  });
});

describe("Badge, StatusBadge, ErrorState, Countdown", () => {
  it("badges always pair an icon with text", () => {
    const { container } = renderWithProviders(
      <>
        <Badge tone="success">Done</Badge>
        <StatusBadge kind="document" status="executed" />
      </>,
    );
    expect(screen.getByText("Signed by everyone")).toBeInTheDocument();
    expect(container.querySelectorAll("[data-tone] svg")).toHaveLength(2);
  });

  it("ErrorState shows friendly text, the reference and a retry, never raw JSON", async () => {
    const user = userEvent.setup();
    const retry = vi.fn();
    const error = new ApiError({ code: "internal", status: 500, message: "Something went wrong on our side. Please try again.", requestId: "req-abc12345" });
    renderWithProviders(<ErrorState error={error} onRetry={retry} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Something went wrong on our side");
    expect(screen.getByText("Reference: req-abc12345")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(retry).toHaveBeenCalled();
    renderWithProviders(<ErrorState error={new Error('{"error":"boom"}')} />);
    expect(screen.queryByText(/boom/)).not.toBeInTheDocument();
  });

  it("Countdown counts days to a date", () => {
    renderWithProviders(<Countdown date="2026-12-01" today={new Date(2026, 10, 23)} label="83(b) due" />);
    expect(screen.getByText("8 days left")).toBeInTheDocument();
    act(() => undefined);
  });
});
