import pkg from "../package.json";

/** The complete approved npm set (ADR-0025, carrying over ADR-0018). */
const ADR_0025 = {
  dependencies: [
    "react",
    "react-dom",
    "react-router-dom",
    "@tanstack/react-query",
    "@radix-ui/react-dialog",
    "@radix-ui/react-tabs",
    "@radix-ui/react-dropdown-menu",
    "@radix-ui/react-select",
    "@radix-ui/react-tooltip",
    "@radix-ui/react-toast",
    "@radix-ui/react-checkbox",
    "@radix-ui/react-progress",
    "@radix-ui/react-avatar",
    "@radix-ui/react-scroll-area",
    "@radix-ui/react-slot",
    "lucide-react",
    "recharts",
    "react-markdown",
    "clsx",
    "tailwind-merge",
    "class-variance-authority",
    "@fontsource-variable/inter",
    "react-hook-form",
    "zod",
    "@hookform/resolvers",
    "@radix-ui/react-label",
    "@radix-ui/react-switch",
    "@radix-ui/react-radio-group",
    "@radix-ui/react-popover",
  ],
  devDependencies: [
    "vite",
    "@vitejs/plugin-react",
    "typescript",
    "@types/react",
    "@types/react-dom",
    "tailwindcss",
    "postcss",
    "autoprefixer",
    "@tailwindcss/typography",
    "vitest",
    "jsdom",
    "@testing-library/react",
    "@testing-library/dom",
    "@testing-library/jest-dom",
    "@testing-library/user-event",
  ],
};

describe("package.json (ADR-0025)", () => {
  it("has exactly the approved dependency names", () => {
    expect(Object.keys(pkg.dependencies).sort()).toEqual([...ADR_0025.dependencies].sort());
    expect(Object.keys(pkg.devDependencies).sort()).toEqual([...ADR_0025.devDependencies].sort());
  });

  it("has the ADR-0018 scripts", () => {
    expect(pkg.scripts).toEqual({
      dev: "vite",
      build: "tsc -b && vite build",
      preview: "vite preview",
      test: "vitest run",
      typecheck: "tsc -b --noEmit",
    });
  });
});
