import Link from "next/link";
import type { Instrument } from "@/lib/api/client";
import { displayName, stockHref, subLine } from "@/lib/format";
import { Badge } from "./ui";

export function MarketDot({ market }: { market: string }) {
  return (
    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-card-2 text-[11px] font-bold text-ink-2">
      {market}
    </span>
  );
}

export default function StockRow({ i, right, href = true }: { i: Instrument; right?: React.ReactNode; href?: boolean }) {
  const body = (
    <>
      <MarketDot market={i.market} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5">
          <span className="truncate text-[15px] font-semibold">{displayName(i)}</span>
          {!i.is_listed && <Badge tone="warn">Not listed</Badge>}
        </div>
        <div className="truncate text-[13px] text-ink-3">{subLine(i)}</div>
      </div>
    </>
  );
  return (
    <li className="flex items-center gap-3 py-2.5">
      {href ? (
        <Link href={stockHref(i)} className="flex min-w-0 flex-1 items-center gap-3">{body}</Link>
      ) : (
        <div className="flex min-w-0 flex-1 items-center gap-3">{body}</div>
      )}
      {right}
    </li>
  );
}
