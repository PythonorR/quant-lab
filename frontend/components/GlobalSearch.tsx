"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { api, type Instrument } from "@/lib/api/client";
import { displayName, stockHref, subLine } from "@/lib/format";
import { MarketDot } from "./StockRow";

/** Search box in the top bar with an instant results dropdown. */
export default function GlobalSearch() {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [results, setResults] = useState<Instrument[]>([]);
  const [hi, setHi] = useState(0);
  const box = useRef<HTMLDivElement>(null);
  const router = useRouter();

  useEffect(() => {
    const query = q.trim();
    if (!query) return;
    let cancelled = false;
    const t = setTimeout(() => {
      api.search(query).then((r) => { if (!cancelled) { setResults(r.slice(0, 8)); setHi(0); } }).catch(() => {});
    }, 150);
    return () => { cancelled = true; clearTimeout(t); };
  }, [q]);

  useEffect(() => {
    const close = (e: MouseEvent) => { if (box.current && !box.current.contains(e.target as Node)) setOpen(false); };
    const key = (e: KeyboardEvent) => {
      if (e.key === "/" && !(e.target instanceof HTMLInputElement)) {
        e.preventDefault();
        box.current?.querySelector("input")?.focus();
      }
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", key);
    return () => { document.removeEventListener("mousedown", close); document.removeEventListener("keydown", key); };
  }, []);

  const shown = q.trim() ? results : [];
  const go = (i: Instrument) => { setOpen(false); setQ(""); router.push(stockHref(i)); };

  return (
    <div ref={box} className="relative">
      <div className="flex h-10 w-[min(52vw,320px)] items-center gap-2 rounded-xl bg-card px-3 ring-1 ring-line focus-within:ring-brand">
        <svg viewBox="0 0 24 24" className="h-4 w-4 shrink-0 text-ink-3" fill="none" stroke="currentColor" strokeWidth={2.2} aria-hidden>
          <path d="M10.5 18a7.5 7.5 0 1 1 0-15 7.5 7.5 0 0 1 0 15zm5.3-2.2L21 21" strokeLinecap="round" />
        </svg>
        <input
          value={q}
          onChange={(e) => { setQ(e.target.value); setOpen(true); }}
          onFocus={() => setOpen(true)}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") { e.preventDefault(); setHi((h) => Math.min(h + 1, shown.length - 1)); }
            if (e.key === "ArrowUp") { e.preventDefault(); setHi((h) => Math.max(h - 1, 0)); }
            if (e.key === "Enter" && shown[hi]) go(shown[hi]);
            if (e.key === "Escape") setOpen(false);
          }}
          placeholder="Search stocks"
          aria-label="Search stocks"
          className="w-full bg-transparent text-[14px] outline-none placeholder:text-ink-3"
        />
        <kbd className="hidden rounded border border-line px-1.5 text-[11px] text-ink-3 md:block">/</kbd>
      </div>
      {open && q.trim() && (
        <div className="absolute right-0 top-12 z-40 w-[min(92vw,420px)] overflow-hidden rounded-2xl border border-line bg-card shadow-2xl">
          {shown.length === 0 ? (
            <p className="px-4 py-5 text-center text-[13px] text-ink-3">No stocks match “{q.trim()}”.</p>
          ) : (
            <ul className="py-1">
              {shown.map((i, k) => (
                <li key={i.id}>
                  <button onMouseEnter={() => setHi(k)} onClick={() => go(i)}
                          className={`flex w-full items-center gap-3 px-4 py-2.5 text-left ${k === hi ? "bg-card-2" : ""}`}>
                    <MarketDot market={i.market} />
                    <div className="min-w-0">
                      <div className="truncate text-[14px] font-semibold">{displayName(i)}</div>
                      <div className="truncate text-[12px] text-ink-3">{subLine(i)}</div>
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
          <Link href={`/stocks?q=${encodeURIComponent(q.trim())}`} onClick={() => setOpen(false)}
                className="block border-t border-line px-4 py-2.5 text-[13px] font-semibold text-brand">
            See all results
          </Link>
        </div>
      )}
    </div>
  );
}
