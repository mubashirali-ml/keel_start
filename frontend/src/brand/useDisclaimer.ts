import { disclaimerLine } from "./brand";
import { useBrandName } from "./BrandName";

/** "Not legal advice. {brand} is not a law firm." with the configured brand. */
export function useDisclaimer(): string {
  return disclaimerLine(useBrandName());
}
