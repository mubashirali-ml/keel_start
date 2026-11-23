/**
 * A tiny `matchMedia` for jsdom that evaluates width and color-scheme queries against a
 * configurable viewport, so responsive components can be tested.
 */
let width = 1280;
let dark = false;

function evaluate(query: string): boolean {
  return query
    .split(",")
    .some((part) =>
      part.split(/\band\b/).every((cond) => {
        const c = cond.trim().replace(/^\(|\)$/g, "");
        let m = /^max-width:\s*([\d.]+)px$/.exec(c);
        if (m) return width <= Number(m[1]);
        m = /^min-width:\s*([\d.]+)px$/.exec(c);
        if (m) return width >= Number(m[1]);
        if (c === "prefers-color-scheme: dark") return dark;
        if (c === "prefers-color-scheme: light") return !dark;
        if (c === "prefers-reduced-motion: reduce") return false;
        return false;
      }),
    );
}

export function setViewport(px: number, options: { dark?: boolean } = {}): void {
  width = px;
  dark = options.dark ?? false;
  window.matchMedia = (query: string) =>
    ({
      matches: evaluate(query),
      media: query,
      onchange: null,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      addListener: () => undefined,
      removeListener: () => undefined,
      dispatchEvent: () => false,
    }) as MediaQueryList;
}
