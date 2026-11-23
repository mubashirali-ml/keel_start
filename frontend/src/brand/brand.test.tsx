import { screen } from "@testing-library/react";

import { mockApi } from "@/test/mockFetch";
import { renderWithProviders } from "@/test/renderWithProviders";

import { BRAND_FALLBACK_NAME, TAGLINE, brandSlug, disclaimerLine, footerLine, landingTitle, pageTitle } from "./brand";
import { Logo } from "./Logo";
import { LogoMark } from "./LogoMark";

// Every source file under src/ (raw text), via Vite's glob import.
const SOURCES = import.meta.glob("/src/**/*.{ts,tsx,css}", { query: "?raw", import: "default", eager: true }) as Record<string, string>;
const isTest = (path: string) => /\.test\.(ts|tsx)$/.test(path) || path.startsWith("/src/test/");

describe("brand (ADR-0041)", () => {
  it("spells the product name only inside src/brand/ (tests excepted)", () => {
    const offenders = Object.entries(SOURCES)
      .filter(([path]) => !path.startsWith("/src/brand/") && !isTest(path))
      .filter(([, text]) => text.includes("Keelstart"))
      .map(([path]) => path);
    expect(Object.keys(SOURCES).length).toBeGreaterThan(40);
    expect(offenders).toEqual([]);
  });

  it("never mentions the old name", () => {
    const old = ["Char", "terly"].join("");
    const offenders = Object.entries(SOURCES).filter(([, text]) => text.includes(old)).map(([path]) => path);
    expect(offenders).toEqual([]);
  });

  it("builds titles, tagline, disclaimer and footer from one name", () => {
    expect(BRAND_FALLBACK_NAME).toBe("Keelstart");
    expect(TAGLINE).toBe("Launch your company with a team of AI agents");
    expect(pageTitle("Pricing")).toBe("Pricing · Keelstart");
    expect(pageTitle("Pricing", "Other")).toBe("Pricing · Other");
    expect(landingTitle()).toBe("Keelstart · Launch your company with a team of AI agents");
    expect(disclaimerLine()).toBe("Not legal advice. Keelstart is not a law firm.");
    expect(footerLine(2026)).toBe("© 2026 [COMPANY LEGAL NAME]. Keelstart is a product of [COMPANY LEGAL NAME].");
    expect(brandSlug("Keel Start!")).toBe("keel-start");
  });

  it("draws the mark as flat currentColor shapes: sail, hull and keel", () => {
    const { container } = renderWithProviders(<LogoMark size={16} />);
    const svg = container.querySelector("svg[data-logo-mark]")!;
    expect(svg.getAttribute("fill")).toBe("currentColor");
    expect(svg.getAttribute("width")).toBe("16");
    expect(svg.querySelectorAll("path")).toHaveLength(3);
    expect(container.innerHTML).not.toMatch(/gradient/i);
    expect(svg).toHaveAttribute("aria-hidden", "true");
  });

  it("shows the configured brand name next to the mark, with the compiled fallback", async () => {
    mockApi({ "GET /api/config": { brand_name: "Renamed" } });
    renderWithProviders(<Logo />);
    expect(screen.getByRole("img", { name: /Keelstart|Renamed/ })).toBeInTheDocument();
    expect(await screen.findByRole("img", { name: "Renamed" })).toBeInTheDocument();
  });

  it("falls back to the compiled name while /api/config does not exist", async () => {
    mockApi({});
    renderWithProviders(<Logo />);
    expect(await screen.findByRole("img", { name: "Keelstart" })).toBeInTheDocument();
  });
});
