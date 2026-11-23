import { screen } from "@testing-library/react";

import * as design from "@/design";
import { mockApi } from "@/test/mockFetch";
import { renderWithProviders } from "@/test/renderWithProviders";

import DesignGallery, { GALLERY_SECTIONS } from "./DesignGallery";

// Exports that are helpers, providers or parts of a component shown under another name.
const NOT_SECTIONS = new Set([
  "focusRing",
  "focusRingInset",
  "initials",
  "buttonVariants",
  "CardContent",
  "CardDescription",
  "CardFooter",
  "CardHeader",
  "CardTitle",
  "DialogClose",
  "DialogContent",
  "DialogTrigger",
  "useZodForm",
  "Label",
  "MenuContent",
  "MenuGroup",
  "MenuItem",
  "MenuLabel",
  "MenuSeparator",
  "MenuTrigger",
  "isPlanRequired",
  "planGateCopy",
  "PopoverClose",
  "PopoverContent",
  "PopoverTrigger",
  "Spinner",
  "LoadingBlock",
  "STATUS_STYLES",
  "TabsContent",
  "TabsList",
  "TabsTrigger",
  "ToastProvider",
  "useToast",
  "TooltipProvider",
  "VisuallyHidden",
]);

describe("/design gallery", () => {
  it("has a section for every shared component", () => {
    const components = Object.keys(design).filter((name) => !NOT_SECTIONS.has(name));
    const missing = components.filter((name) => !(GALLERY_SECTIONS as readonly string[]).includes(name));
    expect(missing).toEqual([]);
    for (const required of ["TrustNote", "PlanGate", "Banner", "FormField", "Switch", "RadioGroup", "Popover", "Logo"]) {
      expect(GALLERY_SECTIONS).toContain(required);
    }
  });

  it("renders every section with its heading, the logo variants and states", () => {
    mockApi({});
    renderWithProviders(<DesignGallery />, { route: "/design" });
    for (const name of GALLERY_SECTIONS) {
      expect(screen.getByRole("heading", { level: 2, name })).toBeInTheDocument();
    }
    for (const variant of ["light", "dark", "one-colour"]) {
      expect(document.querySelector(`[data-logo-variant="${variant}"] [data-logo-mark]`)).not.toBeNull();
    }
    expect(document.querySelector('[data-logo-variant="dark"]')).toHaveClass("dark");
    expect(screen.getByRole("img", { name: /mark at 16 px/ })).toHaveAttribute("width", "16");
    expect(screen.getByRole("img", { name: /mark at 32 px/ })).toHaveAttribute("width", "32");
    expect(document.querySelectorAll('[data-state="empty"]').length).toBeGreaterThan(0);
    expect(document.querySelectorAll('[data-state="error"]').length).toBeGreaterThan(0);
    expect(document.querySelectorAll('[data-state="loading"]').length).toBeGreaterThan(0);
  });
});
