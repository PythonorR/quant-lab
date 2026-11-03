// Display helpers for price bars (not used by the backtest engine, which lives in the backend).
import type { Prices } from "./api/client";

export type Bar = { time: string; open: number; high: number; low: number; close: number; volume: number };
export type Interval = "D" | "W" | "M";

/** Adjusted OHLC. The newest adjusted close equals the real close, so recent prices read naturally. */
export function toBars(p: Prices): Bar[] {
  return p.bars.map((b) => ({
    time: b.date, open: b.adj_open, high: b.adj_high, low: b.adj_low, close: b.adj_close, volume: b.volume,
  }));
}

function weekKey(d: string) {
  const t = new Date(d + "T00:00:00Z");
  const day = (t.getUTCDay() + 6) % 7; // Monday = 0
  t.setUTCDate(t.getUTCDate() - day);
  return t.toISOString().slice(0, 10);
}

export function aggregate(bars: Bar[], interval: Interval): Bar[] {
  if (interval === "D") return bars;
  const key = interval === "W" ? weekKey : (d: string) => d.slice(0, 7);
  const out: Bar[] = [];
  let curKey = "";
  for (const b of bars) {
    const k = key(b.time);
    const last = out[out.length - 1];
    if (k !== curKey || !last) {
      out.push({ ...b });
      curKey = k;
    } else {
      last.high = Math.max(last.high, b.high);
      last.low = Math.min(last.low, b.low);
      last.close = b.close;
      last.volume += b.volume;
    }
  }
  return out;
}

export function movingAverage(bars: Bar[], n: number) {
  const out: { time: string; value: number }[] = [];
  let sum = 0;
  bars.forEach((b, i) => {
    sum += b.close;
    if (i >= n) sum -= bars[i - n].close;
    if (i >= n - 1) out.push({ time: b.time, value: sum / n });
  });
  return out;
}

/** Summary numbers for the stock header. */
export function stats(bars: Bar[]) {
  if (bars.length === 0) return null;
  const last = bars[bars.length - 1];
  const prev = bars.length > 1 ? bars[bars.length - 2] : null;
  const year = bars.slice(-252);
  return {
    last,
    change: prev ? last.close - prev.close : 0,
    changePct: prev ? last.close / prev.close - 1 : 0,
    yearLow: Math.min(...year.map((b) => b.low)),
    yearHigh: Math.max(...year.map((b) => b.high)),
  };
}
