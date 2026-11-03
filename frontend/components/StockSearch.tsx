"use client";

import { useEffect, useState } from "react";
import { api, type Instrument } from "@/lib/api/client";
import StockRow from "./StockRow";

type Props = {
  initialQuery?: string;
  onQueryChange?: (q: string) => void;
  /** When given, rows show an action button instead of linking to the stock page. */
  action?: { label: string; onPick: (i: Instrument) => void; isDone?: (i: Instrument) => boolean };
  autoFocus?: boolean;
};

export default function StockSearch({ initialQuery = "", onQueryChange, action, autoFocus }: Props) {
  const [q, setQ] = useState(initialQuery);
  const [market, setMarket] = useState<"" | "KR" | "US">("");
  const [results, setResults] = useState<Instrument[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const query = q.trim();
    if (!query) return;
    let cancelled = false;
    const t = setTimeout(() => {
      api.search(query, market || undefined)
        .then((r) => !cancelled && (setResults(r), setError(null)))
        .catch((e) => !cancelled && setError(e.message));
    }, 200);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [q, market]);

  const shown = q.trim() ? results : null;

  return (
    <div>
      <div className="flex items-center gap-2 rounded-2xl border border-line bg-card px-4 py-3 focus-within:border-brand">
        <svg viewBox="0 0 24 24" className="h-5 w-5 text-ink-3" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden>
          <path d="M10.5 18a7.5 7.5 0 1 1 0-15 7.5 7.5 0 0 1 0 15zm5.3-2.2L21 21" strokeLinecap="round" />
        </svg>
        <input
          value={q}
          autoFocus={autoFocus}
          onChange={(e) => {
            setQ(e.target.value);
            onQueryChange?.(e.target.value);
          }}
          placeholder="Company name or ticker (e.g. Samsung, AAPL)"
          className="w-full bg-transparent text-[16px] outline-none placeholder:text-ink-3"
          aria-label="Search stocks"
        />
      </div>
      <div className="mt-3 flex gap-2">
        {(["", "KR", "US"] as const).map((m) => (
          <button key={m} onClick={() => setMarket(m)}
                  className={`rounded-full px-3.5 py-1.5 text-[13px] font-semibold ${
                    market === m ? "bg-ink text-page" : "border border-line bg-card text-ink-2"}`}>
            {m === "" ? "All" : m === "KR" ? "Korea" : "US"}
          </button>
        ))}
      </div>
      {error && <p className="mt-3 text-sm text-bad">{error}</p>}
      {shown && (
        <div className="mt-3 rounded-2xl border border-line bg-card px-4 py-1">
          {shown.length === 0 ? (
            <p className="py-6 text-center text-sm text-ink-3">No stocks match “{q.trim()}”.</p>
          ) : (
            <ul className="divide-y divide-line">
              {shown.map((i) => (
                <StockRow key={i.id} i={i} href={!action}
                  right={action && (
                    action.isDone?.(i) ? <span className="text-[13px] text-ink-3">Added</span> : (
                      <button onClick={() => action.onPick(i)}
                              className="rounded-lg bg-brand-soft px-3 py-1.5 text-[13px] font-semibold text-brand">
                        {action.label}
                      </button>
                    ))} />
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
