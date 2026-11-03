import Link from "next/link";
import { Badge, Card } from "@/components/ui";

const STEPS = [
  { n: 1, title: "Build a strategy", body: "Write when to buy and when to sell, in plain sentences." },
  { n: 2, title: "Test on past data", body: "See the win rate together with average win, average loss and the worst drop." },
  { n: 3, title: "Paper trade", body: "Run it with virtual money on new data, every trading day." },
  { n: 4, title: "Review experiments", body: "Every test is saved. Tweak it, compare versions, try again." },
];

export default function Home() {
  return (
    <div className="space-y-6">
      <section className="grid items-center gap-6 rounded-3xl border border-line bg-card px-6 py-10 md:grid-cols-[1.2fr_1fr] md:px-10">
        <div>
          <Badge tone="brand">Research tool · no coding</Badge>
          <h1 className="mt-3 text-[30px] font-extrabold leading-[1.2] tracking-tight md:text-[40px]">
            Your own investing ideas,
            <br />
            tested on real history.
          </h1>
          <p className="mt-3 max-w-md text-[15px] text-ink-2">
            Describe a rule like “buy when it falls 3% in a day, sell at +5% or −3%”, and see how it would have done.
          </p>
          <div className="mt-6 flex flex-wrap gap-2">
            <Link href="/stocks" className="rounded-xl bg-brand px-5 py-3 text-[15px] font-semibold text-white hover:brightness-110">
              Find a stock
            </Link>
            <Link href="/lists" className="rounded-xl bg-card-2 px-5 py-3 text-[15px] font-semibold text-ink-2 hover:text-ink">
              Browse lists
            </Link>
          </div>
        </div>
        <HeroArt />
      </section>

      <section>
        <h2 className="mb-3 text-[18px] font-bold">How it works</h2>
        <ol className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((s) => (
            <li key={s.n}>
              <Card className="h-full">
                <div className="flex items-center justify-between">
                  <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-soft text-[14px] font-bold text-brand">
                    {s.n}
                  </span>
                  <Badge>Coming soon</Badge>
                </div>
                <h3 className="mt-3 text-[16px] font-bold">{s.title}</h3>
                <p className="mt-1 text-[13px] leading-relaxed text-ink-3">{s.body}</p>
              </Card>
            </li>
          ))}
        </ol>
      </section>

      <section className="grid gap-3 md:grid-cols-2">
        <Link href="/stocks" className="group rounded-2xl border border-line bg-card p-5 hover:border-brand">
          <div className="text-[16px] font-bold">Stocks <span className="text-ink-3 group-hover:text-brand">→</span></div>
          <p className="mt-1 text-[13px] text-ink-3">Search every Korean and US stock, see its chart and store its price history.</p>
        </Link>
        <Link href="/lists" className="group rounded-2xl border border-line bg-card p-5 hover:border-brand">
          <div className="text-[16px] font-bold">Lists <span className="text-ink-3 group-hover:text-brand">→</span></div>
          <p className="mt-1 text-[13px] text-ink-3">S&amp;P 500, Nasdaq 100, KOSPI 200, KOSDAQ 150 and your own watchlists.</p>
        </Link>
      </section>
    </div>
  );
}

/** Decorative mini chart (illustration only, not data). */
function HeroArt() {
  const candles = [42, 48, 45, 52, 50, 58, 55, 63, 60, 57, 66, 72, 69, 78];
  return (
    <svg viewBox="0 0 300 170" className="hidden w-full md:block" aria-hidden>
      <line x1="0" y1="150" x2="300" y2="150" stroke="var(--line)" />
      {candles.map((v, i) => {
        const prev = candles[i - 1] ?? v - 3;
        const up = v >= prev;
        const x = 12 + i * 20;
        const top = 160 - Math.max(v, prev) * 1.7;
        const h = Math.max(4, Math.abs(v - prev) * 1.7);
        return (
          <g key={i}>
            <line x1={x} x2={x} y1={top - 8} y2={top + h + 8} stroke={up ? "var(--up)" : "var(--down)"} strokeWidth="1.5" />
            <rect x={x - 5} y={top} width="10" height={h} rx="2" fill={up ? "var(--up)" : "var(--down)"} />
          </g>
        );
      })}
      <path d="M12 92 C 80 80, 140 70, 200 50 S 280 25, 292 22" fill="none" stroke="var(--brand)" strokeWidth="2.5"
            strokeLinecap="round" strokeDasharray="5 5" />
      <g transform="translate(205 102)">
        <rect width="86" height="42" rx="10" fill="var(--panel)" stroke="var(--line)" />
        <text x="12" y="17" fontSize="10" fill="var(--ink-3)">Win rate</text>
        <text x="12" y="33" fontSize="14" fontWeight="700" fill="var(--ink)">? %</text>
      </g>
    </svg>
  );
}
