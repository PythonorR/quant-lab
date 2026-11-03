import Link from "next/link";
import type { ReactNode } from "react";

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`rounded-2xl border border-line bg-card p-5 ${className}`}>{children}</section>;
}

export function PanelTitle({ children, right }: { children: ReactNode; right?: ReactNode }) {
  return (
    <div className="mb-3 flex items-center justify-between gap-3">
      <h2 className="text-[16px] font-bold">{children}</h2>
      {right}
    </div>
  );
}

export function PageTitle({ children, sub, right }: { children: ReactNode; sub?: ReactNode; right?: ReactNode }) {
  return (
    <header className="mb-5 mt-1 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-[26px] font-bold leading-tight">{children}</h1>
        {sub && <p className="mt-1 text-[14px] text-ink-3">{sub}</p>}
      </div>
      {right}
    </header>
  );
}

export function BackLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link href={href} className="mb-3 inline-flex items-center gap-1 text-[14px] text-ink-3 hover:text-ink-2">
      <span aria-hidden>‹</span> {children}
    </Link>
  );
}

export type Tone = "neutral" | "brand" | "good" | "bad" | "warn";
const TONES: Record<Tone, string> = {
  neutral: "bg-card-2 text-ink-2",
  brand: "bg-brand-soft text-brand",
  good: "bg-good-soft text-good",
  bad: "bg-bad-soft text-bad",
  warn: "bg-warn-soft text-warn",
};

export function Badge({ tone = "neutral", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span className={`inline-block shrink-0 whitespace-nowrap rounded-md px-1.5 py-0.5 text-[11px] font-semibold ${TONES[tone]}`}>
      {children}
    </span>
  );
}

export function Notice({ tone = "warn", children }: { tone?: Tone; children: ReactNode }) {
  return <div className={`rounded-xl px-4 py-3 text-[13px] leading-relaxed ${TONES[tone]}`}>{children}</div>;
}

export function Button({
  children, onClick, disabled, variant = "primary", type = "button", className = "",
}: {
  children: ReactNode; onClick?: () => void; disabled?: boolean; variant?: "primary" | "secondary";
  type?: "button" | "submit"; className?: string;
}) {
  const v = variant === "primary" ? "bg-brand text-white hover:brightness-110 active:brightness-95"
    : "bg-card-2 text-ink-2 hover:text-ink";
  return (
    <button type={type} onClick={onClick} disabled={disabled}
            className={`rounded-xl px-4 py-2.5 text-[15px] font-semibold transition disabled:opacity-40 ${v} ${className}`}>
      {children}
    </button>
  );
}

export function Segmented<T extends string>({
  value, options, onChange,
}: { value: T; options: { value: T; label: string }[]; onChange: (v: T) => void }) {
  return (
    <div className="inline-flex rounded-lg bg-card-2 p-0.5">
      {options.map((o) => (
        <button key={o.value} onClick={() => onChange(o.value)}
                className={`rounded-md px-3 py-1 text-[13px] font-semibold ${
                  value === o.value ? "bg-card text-ink shadow-sm" : "text-ink-3 hover:text-ink-2"}`}>
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function Skeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="animate-pulse space-y-3 rounded-2xl border border-line bg-card p-5">
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="h-4 rounded bg-card-2" style={{ width: `${90 - i * 15}%` }} />
      ))}
    </div>
  );
}

export function ErrorBox({ message }: { message: string }) {
  return <Notice tone="bad">{message}</Notice>;
}
