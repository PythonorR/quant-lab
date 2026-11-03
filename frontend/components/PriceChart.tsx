"use client";

import {
  CandlestickSeries, ColorType, CrosshairMode, HistogramSeries, LineSeries, createChart,
  type IChartApi, type ISeriesApi, type MouseEventParams, type Time,
} from "lightweight-charts";
import { useEffect, useMemo, useRef, useState } from "react";
import { aggregate, movingAverage, type Bar, type Interval } from "@/lib/bars";
import { formatPrice } from "@/lib/format";
import { cssVar } from "@/lib/theme";

const MAS = [
  { n: 5, v: "--ma5" },
  { n: 20, v: "--ma20" },
  { n: 60, v: "--ma60" },
  { n: 120, v: "--ma120" },
] as const;

const compact = (v: number) =>
  v.toLocaleString("en-US", { notation: "compact", maximumFractionDigits: 1 });

function palette() {
  return {
    text: cssVar("--ink-3"), grid: cssVar("--line"), up: cssVar("--up"), down: cssVar("--down"),
    mas: MAS.map((m) => cssVar(m.v)),
  };
}

/** Candlestick chart with moving averages and a volume pane. Follows the light/dark theme. */
export default function PriceChart({ bars, interval, currency }: { bars: Bar[]; interval: Interval; currency: string }) {
  const el = useRef<HTMLDivElement>(null);
  const chart = useRef<IChartApi | null>(null);
  const series = useRef<{
    candles: ISeriesApi<"Candlestick">; volume: ISeriesApi<"Histogram">; mas: ISeriesApi<"Line">[];
  } | null>(null);
  const data = useMemo(() => aggregate(bars, interval), [bars, interval]);
  const [hover, setHover] = useState<Bar | null>(null);
  const [tick, setTick] = useState(0); // bumps when the theme changes, to recolour volume bars
  const shown = hover ?? data[data.length - 1];

  // Create once.
  useEffect(() => {
    if (!el.current) return;
    const p = palette();
    const c = createChart(el.current, {
      autoSize: true,
      layout: { background: { type: ColorType.Solid, color: "transparent" }, textColor: p.text, fontSize: 12,
                attributionLogo: false, panes: { separatorColor: p.grid } },
      grid: { vertLines: { color: p.grid }, horzLines: { color: p.grid } },
      rightPriceScale: { borderVisible: false },
      timeScale: { borderVisible: false, rightOffset: 4 },
      crosshair: { mode: CrosshairMode.Normal },
    });
    const priceFormat = { type: "custom" as const, minMove: currency === "KRW" ? 1 : 0.01,
                          formatter: (v: number) => formatPrice(v, currency) };
    const candles = c.addSeries(CandlestickSeries, {
      upColor: p.up, downColor: p.down, borderUpColor: p.up, borderDownColor: p.down,
      wickUpColor: p.up, wickDownColor: p.down, priceFormat,
    });
    const mas = MAS.map((_, k) => c.addSeries(LineSeries, {
      color: p.mas[k], lineWidth: 1, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false, priceFormat,
    }));
    const volume = c.addSeries(HistogramSeries, {
      priceFormat: { type: "custom", minMove: 1, formatter: compact }, priceLineVisible: false,
    }, 1);
    c.panes()[0].setStretchFactor(3);
    c.panes()[1].setStretchFactor(1);
    chart.current = c;
    series.current = { candles, volume, mas };

    const onMove = (e: MouseEventParams<Time>) => {
      const d = e.seriesData.get(candles) as { open: number; high: number; low: number; close: number } | undefined;
      setHover(d && e.time ? { time: String(e.time), ...d, volume: 0 } : null);
    };
    c.subscribeCrosshairMove(onMove);

    // Re-colour when the theme changes.
    const obs = new MutationObserver(() => {
      const q = palette();
      c.applyOptions({ layout: { textColor: q.text, panes: { separatorColor: q.grid } },
                       grid: { vertLines: { color: q.grid }, horzLines: { color: q.grid } } });
      candles.applyOptions({ upColor: q.up, downColor: q.down, borderUpColor: q.up, borderDownColor: q.down,
                             wickUpColor: q.up, wickDownColor: q.down });
      mas.forEach((s, k) => s.applyOptions({ color: q.mas[k] }));
      setTick((t) => t + 1);
    });
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => { obs.disconnect(); c.remove(); chart.current = null; series.current = null; };
  }, [currency]);

  // Load data.
  useEffect(() => {
    const s = series.current;
    const c = chart.current;
    if (!s || !c) return;
    const p = palette();
    s.candles.setData(data.map(({ time, open, high, low, close }) => ({ time, open, high, low, close })));
    s.volume.setData(data.map((b, i) => ({
      time: b.time, value: b.volume,
      color: (i > 0 ? b.close >= data[i - 1].close : b.close >= b.open) ? p.up : p.down,
    })));
    MAS.forEach((m, k) => s.mas[k].setData(movingAverage(data, m.n)));
    const visible = interval === "D" ? 130 : interval === "W" ? 104 : 60;
    if (data.length > visible) c.timeScale().setVisibleLogicalRange({ from: data.length - visible, to: data.length + 3 });
    else c.timeScale().fitContent();
  }, [data, interval, tick]);

  return (
    <div className="relative">
      <div className="pointer-events-none absolute left-1 top-0 z-10 flex flex-wrap gap-x-3 gap-y-0.5 text-[12px]">
        {shown && (
          <span className="tabular text-ink-2">
            {shown.time} · O {formatPrice(shown.open, currency)} H {formatPrice(shown.high, currency)} L{" "}
            {formatPrice(shown.low, currency)} C <b className="text-ink">{formatPrice(shown.close, currency)}</b>
          </span>
        )}
        <span className="flex gap-2">
          {MAS.map((m) => <span key={m.n} style={{ color: `var(${m.v})` }}>MA{m.n}</span>)}
        </span>
      </div>
      <div ref={el} className="h-[420px] w-full pt-5 md:h-[480px]" />
    </div>
  );
}
