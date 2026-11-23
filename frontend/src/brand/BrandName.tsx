import { useConfig } from "@/api/hooks";

import { BRAND_FALLBACK_NAME } from "./brand";

/** The product name from `PublicConfig.brand_name`, with the compiled fallback. */
export function useBrandName(): string {
  const { data } = useConfig();
  return data?.brand_name || BRAND_FALLBACK_NAME;
}

/** Renders the product name as text (for copy such as "Signed with {BrandName}"). */
export function BrandName() {
  return <>{useBrandName()}</>;
}
