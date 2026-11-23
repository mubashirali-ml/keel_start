import type { ReactNode } from "react";

import { cn } from "@/lib/cn";
import { QUERIES, useMediaQuery } from "@/lib/useMediaQuery";

export interface TableColumn<T> {
  key: string;
  header: string;
  cell: (row: T) => ReactNode;
  align?: "left" | "right";
  /** Hide the label in the stacked (phone) layout, e.g. for an actions column. */
  hideLabelWhenStacked?: boolean;
  className?: string;
}

export interface TableProps<T> {
  columns: TableColumn<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  /** Visible or screen-reader caption describing the table. */
  caption: string;
  captionVisible?: boolean;
  empty?: ReactNode;
  className?: string;
}

/**
 * A data table that stacks into cards below 640px (ADR-0019), so nothing scrolls sideways
 * on a phone. Each stacked card repeats the column labels.
 */
export function Table<T>({ columns, rows, rowKey, caption, captionVisible = false, empty, className }: TableProps<T>) {
  const stacked = useMediaQuery(QUERIES.belowSm);

  if (rows.length === 0 && empty) return <>{empty}</>;

  if (stacked) {
    return (
      <div className={cn("grid gap-3", className)} data-layout="stacked">
        <p className={captionVisible ? "text-sm font-medium text-text" : "sr-only"}>{caption}</p>
        <ul className="grid gap-3" aria-label={caption}>
          {rows.map((row) => (
            <li key={rowKey(row)} className="rounded-lg border bg-surface p-4 shadow-sm">
              <dl className="grid gap-2">
                {columns.map((col) => (
                  <div key={col.key} className="flex items-start justify-between gap-4">
                    <dt className={cn("text-xs font-medium uppercase tracking-wide text-text-muted", col.hideLabelWhenStacked && "sr-only")}>
                      {col.header}
                    </dt>
                    <dd className="min-w-0 text-right text-sm text-text">{col.cell(row)}</dd>
                  </div>
                ))}
              </dl>
            </li>
          ))}
        </ul>
      </div>
    );
  }

  return (
    <div className={cn("overflow-hidden rounded-lg border bg-surface shadow-sm", className)} data-layout="table">
      <table className="w-full border-collapse text-sm">
        <caption className={captionVisible ? "px-4 py-3 text-left text-sm font-medium text-text" : "sr-only"}>{caption}</caption>
        <thead className="bg-surface-muted">
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                scope="col"
                className={cn(
                  "border-b px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-text-muted",
                  col.align === "right" ? "text-right" : "text-left",
                  col.className,
                )}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={rowKey(row)} className="border-b last:border-b-0 hover:bg-surface-muted/60">
              {columns.map((col) => (
                <td key={col.key} className={cn("px-4 py-3 align-middle text-text", col.align === "right" && "text-right tabular-nums", col.className)}>
                  {col.cell(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
