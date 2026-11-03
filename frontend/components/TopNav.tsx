"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Suspense } from "react";
import GlobalSearch from "./GlobalSearch";
import ThemeToggle from "./ThemeToggle";

const LINKS = [
  { href: "/", label: "Home" },
  { href: "/stocks", label: "Stocks" },
  { href: "/lists", label: "Lists" },
];
// Later phases; shown so people can see where the product is going.
const SOON = ["Strategies", "Experiments", "Paper trading"];

export default function TopNav() {
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-card-2/90 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-[1320px] items-center gap-2 px-4 md:gap-6 md:px-6">
        <Link href="/" className="flex shrink-0 items-center gap-2">
          <Logo />
          <span className="text-[18px] font-extrabold tracking-tight">QuantLab</span>
        </Link>
        <nav className="hidden items-center gap-1 md:flex">
          <Suspense fallback={<Links path="" />}>
            <ActiveLinks />
          </Suspense>
          {SOON.map((s) => (
            <span key={s} className="cursor-default px-3 py-2 text-[15px] font-medium text-ink-3/60" title="Coming soon">
              {s}
            </span>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-1">
          <GlobalSearch />
          <ThemeToggle />
        </div>
      </div>
      {/* Small screens: the same links in a scrollable row. */}
      <nav className="flex gap-1 overflow-x-auto px-3 pb-2 md:hidden">
        <Suspense fallback={<Links path="" />}>
          <ActiveLinks />
        </Suspense>
      </nav>
    </header>
  );
}

function ActiveLinks() {
  return <Links path={usePathname()} />;
}

function Links({ path }: { path: string }) {
  return (
    <>
      {LINKS.map((l) => {
        const active = l.href === "/" ? path === "/" : path.startsWith(l.href);
        return (
          <Link key={l.href} href={l.href}
                className={`whitespace-nowrap rounded-lg px-3 py-2 text-[15px] font-semibold ${
                  active ? "text-ink" : "text-ink-3 hover:text-ink-2"}`}>
            {l.label}
          </Link>
        );
      })}
    </>
  );
}

function Logo() {
  return (
    <svg viewBox="0 0 32 32" className="h-8 w-8" aria-hidden>
      <rect width="32" height="32" rx="9" fill="var(--brand)" />
      <path d="M8 21l5-6 4 3 7-9" fill="none" stroke="#fff" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="24" cy="9" r="2.2" fill="#fff" />
    </svg>
  );
}
