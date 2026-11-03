"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import DataStatus from "@/components/DataStatus";
import PriceChart from "@/components/PriceChart";
import { Badge, Button, Card, ErrorBox, PanelTitle, Segmented, Skeleton } from "@/components/ui";
import { api, type Prices, type StockDetail, type Watchlist } from "@/lib/api/client";
import { stats, toBars, type Interval } from "@/lib/bars";
import { currencySymbol, displayName, formatDate, formatPrice } from "@/lib/format";

export default function StockView() {
  const { market, ticker } = useParams<{ market: string; ticker: string }>();
  const t = decodeURIComponent(ticker);
  const [detail, setDetail] = useState<StockDetail | null>(null);
  const [prices, setPrices] = useState<Prices | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [interval, setInterval] = useState<Interval>("D");
  const [version, setVersion] = useState(0);
  const reload = useCallback(() => setVersion((v) => v + 1), []);

  useEffect(() => {
    let cancelled = false;
    api.stock(market, t)
      .then(async (d) => {
        if (cancelled) return;
        setDetail(d);
        setError(null);
        if (d.coverage.last_bar) {
          const p = await api.prices(market, t);
          if (!cancelled) setPrices(p);
        }
      })
      .catch((e) => !cancelled && setError((e as Error).message));
    return () => { cancelled = true; };
  }, [market, t, version]);

  const bars = useMemo(() => (prices ? toBars(prices) : []), [prices]);
  const st = useMemo(() => stats(bars), [bars]);

  if (error) return <ErrorBox message={error} />;
  if (!detail) return <Skeleton lines={6} />;
  const i = detail.instrument;
  const cur = i.currency;
  const sym = currencySymbol(cur);
  const dir = !st || st.change === 0 ? "text-ink-2" : st.change > 0 ? "text-up" : "text-down";

  return (
    <div className="space-y-4">
      {/* Header: name, price, ranges */}
      <section className="flex flex-wrap items-end justify-between gap-x-10 gap-y-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-[22px] font-bold md:text-[24px]">{displayName(i)}</h1>
            <span className="text-[15px] text-ink-3">{i.ticker}</span>
            <Badge>{i.exchange ?? i.market}</Badge>
            {!i.is_listed && <Badge tone="warn">Not listed</Badge>}
          </div>
          {i.name_en && i.name_en !== i.name && <p className="text-[13px] text-ink-3">{i.name}</p>}
          {st ? (
            <div className="tabular mt-1 flex flex-wrap items-baseline gap-x-3">
              <span className="text-[32px] font-bold tracking-tight">{sym}{formatPrice(st.last.close, cur)}</span>
              <span className={`text-[16px] font-semibold ${dir}`}>
                {st.change > 0 ? "+" : ""}{formatPrice(st.change, cur)} ({st.change > 0 ? "+" : ""}
                {(st.changePct * 100).toFixed(2)}%)
              </span>
              <span className="text-[13px] text-ink-3">close of {formatDate(st.last.time)}</span>
            </div>
          ) : (
            <p className="mt-2 text-[15px] text-ink-3">No price history stored yet.</p>
          )}
        </div>
        {st && (
          <dl className="tabular grid grid-cols-[auto_1fr] items-center gap-x-4 gap-y-2 text-[13px] w-full sm:w-auto sm:min-w-[420px]">
            <Range label="Day range" low={st.last.low} high={st.last.high} value={st.last.close} cur={cur} />
            <Range label="52-week range" low={st.yearLow} high={st.yearHigh} value={st.last.close} cur={cur} />
            <dt className="text-ink-3">Volume</dt>
            <dd className="font-semibold">{st.last.volume.toLocaleString("en-US")}</dd>
          </dl>
        )}
      </section>

      <div className="grid gap-4 lg:grid-cols-12">
        <div className="space-y-4 lg:col-span-8">
          <Card className="!p-4">
            <PanelTitle right={
              <Segmented value={interval} onChange={setInterval}
                         options={[{ value: "D", label: "Day" }, { value: "W", label: "Week" }, { value: "M", label: "Month" }]} />
            }>
              Chart
            </PanelTitle>
            {bars.length > 0 ? (
              <>
                <PriceChart bars={bars} interval={interval} currency={cur} />
                <p className="mt-2 text-[12px] text-ink-3">
                  Prices adjusted for splits{prices?.adjustment === "splits_and_dividends" ? " and dividends" : ""}, so
                  past prices are comparable with today&apos;s.
                </p>
              </>
            ) : (
              <div className="flex h-[300px] flex-col items-center justify-center gap-2 rounded-xl bg-card-2 text-center">
                <p className="text-[15px] font-semibold">No chart yet</p>
                <p className="max-w-xs text-[13px] text-ink-3">Download the price history (on the right) to see the chart.</p>
              </div>
            )}
          </Card>
          {bars.length > 1 && <DailyTable bars={bars} cur={cur} />}
        </div>

        <div className="space-y-4 lg:col-span-4">
          <DataStatus instrument={i} coverage={detail.coverage} onUpdated={reload} />
          <AddToWatchlist instrumentId={i.id} />
        </div>
      </div>
    </div>
  );
}

function Range({ label, low, high, value, cur }: { label: string; low: number; high: number; value: number; cur: string }) {
  const pos = high > low ? ((value - low) / (high - low)) * 100 : 50;
  return (
    <>
      <dt className="text-ink-3">{label}</dt>
      <dd className="flex items-center gap-2.5">
        <span className="text-right sm:w-20">{formatPrice(low, cur)}</span>
        <span className="relative h-1 min-w-12 flex-1 rounded-full bg-card-2">
          <span className="absolute top-1/2 h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-brand ring-2 ring-card"
                style={{ left: `${Math.min(100, Math.max(0, pos))}%` }} />
        </span>
        <span className="sm:w-20">{formatPrice(high, cur)}</span>
      </dd>
    </>
  );
}

function DailyTable({ bars, cur }: { bars: ReturnType<typeof toBars>; cur: string }) {
  const rows = bars.slice(-61).map((b, k, a) => (k === 0 ? null : { ...b, chg: b.close / a[k - 1].close - 1 }))
    .filter((r): r is NonNullable<typeof r> => r !== null).reverse();
  return (
    <Card className="!p-0">
      <div className="px-5 pt-5"><PanelTitle>Daily prices</PanelTitle></div>
      <div className="max-h-[420px] overflow-y-auto">
        <table className="tabular w-full text-[14px]">
          <thead className="sticky top-0 bg-card text-[12px] text-ink-3">
            <tr className="border-b border-line">
              <th className="px-5 py-2 text-left font-medium">Date</th>
              <th className="px-3 py-2 text-right font-medium">Close</th>
              <th className="px-3 py-2 text-right font-medium">Change</th>
              <th className="hidden px-3 py-2 text-right font-medium sm:table-cell">High</th>
              <th className="hidden px-3 py-2 text-right font-medium sm:table-cell">Low</th>
              <th className="px-5 py-2 text-right font-medium">Volume</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.time} className="border-b border-line/60 last:border-0 hover:bg-card-2">
                <td className="px-5 py-2.5 text-ink-2">{formatDate(r.time)}</td>
                <td className="px-3 py-2.5 text-right font-semibold">{formatPrice(r.close, cur)}</td>
                <td className={`px-3 py-2.5 text-right ${r.chg > 0 ? "text-up" : r.chg < 0 ? "text-down" : "text-ink-3"}`}>
                  {r.chg > 0 ? "+" : ""}{(r.chg * 100).toFixed(2)}%
                </td>
                <td className="hidden px-3 py-2.5 text-right text-ink-2 sm:table-cell">{formatPrice(r.high, cur)}</td>
                <td className="hidden px-3 py-2.5 text-right text-ink-2 sm:table-cell">{formatPrice(r.low, cur)}</td>
                <td className="px-5 py-2.5 text-right text-ink-2">{r.volume.toLocaleString("en-US")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function AddToWatchlist({ instrumentId }: { instrumentId: number }) {
  const [lists, setLists] = useState<Watchlist[] | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  useEffect(() => {
    api.watchlists().then(setLists).catch(() => setLists([]));
  }, []);
  if (!lists) return null;

  const add = async (w: Watchlist | null) => {
    try {
      const target = w ?? (await api.createWatchlist("My watchlist"));
      const updated = await api.addToWatchlist(target.id, instrumentId);
      setLists((ls) => [...(ls ?? []).filter((x) => x.id !== updated.id), updated].sort((a, b) => a.id - b.id));
      setMsg(`Added to “${updated.name}”.`);
    } catch (e) {
      setMsg((e as Error).message);
    }
  };

  return (
    <Card>
      <PanelTitle>Watchlists</PanelTitle>
      <div className="flex flex-wrap gap-2">
        {lists.length === 0 && <Button variant="secondary" onClick={() => add(null)}>+ Add to a new watchlist</Button>}
        {lists.map((w) => {
          const inIt = w.items.some((x) => x.id === instrumentId);
          return (
            <Button key={w.id} variant="secondary" disabled={inIt} onClick={() => add(w)}>
              {inIt ? `✓ In ${w.name}` : `+ ${w.name}`}
            </Button>
          );
        })}
      </div>
      {msg && <p className="mt-2 text-[13px] text-ink-2">{msg}</p>}
    </Card>
  );
}
