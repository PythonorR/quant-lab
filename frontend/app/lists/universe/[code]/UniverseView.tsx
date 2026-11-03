"use client";

import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import StockTable from "@/components/StockTable";
import { Badge, Card, ErrorBox, Notice, PanelTitle, Skeleton } from "@/components/ui";
import { api, type UniverseMembers } from "@/lib/api/client";
import { formatDate } from "@/lib/format";
import DownloadAll from "../../DownloadAll";

const PAGE = 100;

export default function UniverseView() {
  const { code } = useParams<{ code: string }>();
  const [date, setDate] = useState("");
  const [data, setData] = useState<UniverseMembers | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("");
  const [shown, setShown] = useState(PAGE);
  const target = useMemo(() => ({ universe: code }), [code]);

  useEffect(() => {
    api.members(code, date || undefined).then((d) => { setData(d); setError(null); }).catch((e) => setError(e.message));
  }, [code, date]);

  if (error) return <ErrorBox message={error} />;
  if (!data) return <Skeleton lines={5} />;
  const f = filter.trim().toLowerCase();
  const members = f
    ? data.members.filter((m) => [m.ticker, m.name, m.name_en ?? ""].some((s) => s.toLowerCase().includes(f)))
    : data.members;

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <h1 className="text-[26px] font-bold">{data.name}</h1>
        <span className="tabular text-[15px] text-ink-3">{data.members.length.toLocaleString()} stocks</span>
        {data.point_in_time ? <Badge tone="good">Past members included</Badge> : <Badge tone="warn">Today&apos;s members only</Badge>}
      </header>

      <div className="grid gap-4 lg:grid-cols-12">
        <Card className="lg:col-span-8">
          <input value={filter} onChange={(e) => { setFilter(e.target.value); setShown(PAGE); }}
                 placeholder="Filter by name or ticker"
                 className="mb-2 w-full rounded-xl bg-card-2 px-3 py-2.5 text-[15px] outline-none" />
          <StockTable items={members.slice(0, shown)} />
          {members.length > shown && (
            <button onClick={() => setShown((n) => n + PAGE)} className="mt-2 w-full py-2 text-[14px] font-semibold text-brand">
              Show more ({members.length - shown} left)
            </button>
          )}
          {members.length === 0 && <p className="py-6 text-center text-[13px] text-ink-3">No stocks.</p>}
        </Card>

        <div className="space-y-4 lg:col-span-4">
          <Card>
            <PanelTitle>About this list</PanelTitle>
            <dl className="grid grid-cols-2 gap-y-2 text-[14px]">
              <dt className="text-ink-3">Members as of</dt>
              <dd className="text-right font-semibold">{data.as_of_date ? formatDate(data.as_of_date) : "Today"}</dd>
            </dl>
            {data.point_in_time && (
              <label className="mt-3 flex items-center justify-between gap-2 text-[14px]">
                <span className="text-ink-3">Show members on</span>
                <input type="date" value={date} onChange={(e) => setDate(e.target.value)}
                       className="rounded-lg bg-card-2 px-2 py-1.5 text-[14px]" />
              </label>
            )}
            <div className="mt-3 space-y-2">
              {data.warnings.map((w, k) => (
                <Notice key={k} tone={!data.point_in_time && k === 0 ? "warn" : "neutral"}>{w}</Notice>
              ))}
            </div>
          </Card>
          <Card>
            <PanelTitle>Price data</PanelTitle>
            <p className="text-[13px] text-ink-3">
              {data.point_in_time ? "Includes every stock that was a member at any time in the stored history." :
                "Every stock in the list."}
            </p>
            <DownloadAll target={target} />
          </Card>
        </div>
      </div>
    </div>
  );
}
