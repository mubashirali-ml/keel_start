/** The visible focus ring every interactive component uses (`focus-ring` token, ADR-0019). */
export const focusRing =
  "outline-none focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:ring-offset-2 focus-visible:ring-offset-bg";

/** Focus ring for elements inside a tight container (no offset). */
export const focusRingInset = "outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-focus-ring";
