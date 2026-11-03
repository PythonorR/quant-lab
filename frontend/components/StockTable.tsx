import Link from "next/link";
import type { ReactNode } from "react";
import type { Instrument } from "@/lib/api/client";
import { displayName, stockHref } from "@/lib/format";
import { Badge } from "./ui";
import { MarketDot } from "./StockRow";

/** Table of stocks (desktop columns; collapses gracefully on phones). */
export default function StockTable({ items, action }: { items: Instrument[]; action?: (i: Instrument) => ReactNode }) {
  return (
    <table className="w-full text-[14px]">
      <thead className="text-[12px] text-ink-3">
        <tr className="border-b border-line">
          <th className="py-2 text-left font-medium">Name</th>
          <th className="hidden py-2 text-left font-medium sm:table-cell">Ticker</th>
          <th className="hidden py-2 text-left font-medium md:table-cell">Exchange</th>
          {action && <th className="py-2" />}
        </tr>
      </thead>
      <tbody>
        {items.map((i) => (
          <tr key={i.id} className="border-b border-line/60 last:border-0 hover:bg-card-2">
            <td className="py-2.5 pr-3">
              <Link href={stockHref(i)} className="flex items-center gap-3">
                <MarketDot market={i.market} />
                <div className="min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="truncate font-semibold">{displayName(i)}</span>
                    {!i.is_listed && <Badge tone="warn">Not listed</Badge>}
                  </div>
                  <div className="truncate text-[12px] text-ink-3">
                    <span className="sm:hidden">{i.ticker} · </span>
                    {i.name_en && i.name_en !== i.name ? i.name : i.market === "US" ? "US stock" : ""}
                  </div>
                </div>
              </Link>
            </td>
            <td className="tabular hidden py-2.5 pr-3 text-ink-2 sm:table-cell">{i.ticker}</td>
            <td className="hidden py-2.5 pr-3 text-ink-2 md:table-cell">{i.exchange ?? "—"}</td>
            {action && <td className="py-2.5 text-right">{action(i)}</td>}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
