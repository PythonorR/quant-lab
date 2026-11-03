import type { Instrument } from "./api/client";

export const displayName = (i: Instrument) => i.name_en || i.name;

/** Secondary line, e.g. "005930 · KOSPI · 삼성전자" (local name shown when an English name is used). */
export const subLine = (i: Instrument) =>
  [i.ticker, i.exchange, i.name_en && i.name_en !== i.name ? i.name : null].filter(Boolean).join(" · ");

export const stockHref = (i: { market: string; ticker: string }) => `/stocks/${i.market}/${encodeURIComponent(i.ticker)}`;

export function formatPrice(v: number, currency: string) {
  const digits = currency === "KRW" ? 0 : 2;
  return v.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

export const currencySymbol = (c: string) => (c === "KRW" ? "₩" : c === "USD" ? "$" : "");

export function formatDate(d: string) {
  return new Date(d + "T00:00:00").toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
}

export const ADJUSTMENT_LABEL: Record<string, string> = {
  splits_and_dividends: "Adjusted for splits and dividends",
  no_dividends: "Not adjusted for dividends",
};
