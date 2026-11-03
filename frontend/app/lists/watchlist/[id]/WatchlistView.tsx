"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import StockSearch from "@/components/StockSearch";
import StockTable from "@/components/StockTable";
import { Card, ErrorBox, PanelTitle, Skeleton } from "@/components/ui";
import { api, type Watchlist } from "@/lib/api/client";
import DownloadAll from "../../DownloadAll";

export default function WatchlistView() {
  const { id } = useParams<{ id: string }>();
  const wid = Number(id);
  const router = useRouter();
  const [w, setW] = useState<Watchlist | null>(null);
  const [error, setError] = useState<string | null>(null);
  const target = useMemo(() => ({ watchlist_id: wid }), [wid]);
  const key = w?.items.map((i) => i.id).join(",") ?? ""; // remount DownloadAll when items change

  useEffect(() => {
    api.watchlist(wid).then(setW).catch((e) => setError(e.message));
  }, [wid]);

  const act = (p: Promise<Watchlist>) => p.then(setW).catch((e) => setError(e.message));

  if (error) return <ErrorBox message={error} />;
  if (!w) return <Skeleton lines={4} />;
  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-end justify-between gap-2">
        <div className="flex items-baseline gap-3">
          <h1 className="text-[26px] font-bold">{w.name}</h1>
          <span className="text-[15px] text-ink-3">{w.items.length} stocks</span>
        </div>
        <button className="text-[13px] text-ink-3 hover:text-bad" onClick={async () => {
          if (!confirm(`Delete “${w.name}”?`)) return;
          await api.deleteWatchlist(w.id);
          router.push("/lists");
        }}>Delete list</button>
      </header>

      <div className="grid gap-4 lg:grid-cols-12">
        <div className="space-y-4 lg:col-span-7">
          <Card>
            <PanelTitle>Stocks</PanelTitle>
            {w.items.length === 0 ? (
              <p className="py-6 text-center text-[13px] text-ink-3">No stocks yet. Search and add some.</p>
            ) : (
              <StockTable items={w.items} action={(i) => (
                <button onClick={() => act(api.removeFromWatchlist(w.id, i.id))}
                        className="rounded-lg px-2 py-1 text-[13px] text-ink-3 hover:bg-card hover:text-bad"
                        aria-label={`Remove ${i.ticker}`}>Remove</button>
              )} />
            )}
          </Card>
          {w.items.length > 0 && (
            <Card>
              <PanelTitle>Price data</PanelTitle>
              <DownloadAll key={key} target={target} />
            </Card>
          )}
        </div>
        <div className="lg:col-span-5">
          <Card>
            <PanelTitle>Add stocks</PanelTitle>
            <StockSearch action={{
              label: "Add",
              onPick: (i) => act(api.addToWatchlist(w.id, i.id)),
              isDone: (i) => w.items.some((x) => x.id === i.id),
            }} />
          </Card>
        </div>
      </div>
    </div>
  );
}
