import { useEffect } from "react";

import { landingTitle, pageTitle } from "./brand";
import { useBrandName } from "./BrandName";

/** Sets `document.title` to `{page} · {brand}` (or the landing title when `page` is null). */
export function usePageTitle(page: string | null) {
  const brand = useBrandName();
  useEffect(() => {
    document.title = page === null ? landingTitle(brand) : pageTitle(page, brand);
  }, [page, brand]);
}
