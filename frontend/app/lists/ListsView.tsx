"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Badge, Button, Card, ErrorBox, Skeleton } from "@/components/ui";
import { api, type Universe, type Watchlist } from "@/lib/api/client";

export default function ListsView() {
  const [unis, setUnis] = useState<Universe[] | null>(null);
  const [wls, setWls] = useState<Watchlist[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const router = useRouter();

  useEffect(() => {
    api.universes().then(setUnis).catch((e) => setError(e.message));
    api.watchlists().then(setWls).catch((e) => setError(e.message));
  }, []);

  const create = async () => {
    try {
      const w = await api.createWatchlist(name.trim() || "My watchlist");
      router.push(`/lists/watchlist/${w.id}`);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  if (error) return <ErrorBox message={error} />;
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card>
        <h2 className="text-[17px] font-bold">Market lists</h2>
        {!unis ? <div className="mt-3"><Skeleton lines={3} /></div> : (
          <ul className="mt-2 divide-y divide-line">
            {unis.map((u) => (
              <li key={u.code}>
                <Link href={`/lists/universe/${u.code}`} className="-mx-2 flex items-center justify-between rounded-lg px-2 py-3 hover:bg-card-2">
                  <div>
                    <div className="text-[15px] font-semibold">{u.name}</div>
                    <div className="mt-0.5 flex items-center gap-1.5 text-[12px] text-ink-3">
                      {u.member_count > 0 ? (
                        <>
                          <span className="tabular">{u.member_count.toLocaleString()} stocks</span>
                          {u.point_in_time
                            ? <Badge tone="good">Past members included</Badge>
                            : <Badge tone="warn">Today&apos;s members only</Badge>}
                        </>
                      ) : <span>Not downloaded yet</span>}
                    </div>
                  </div>
                  <span className="text-ink-3" aria-hidden>›</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card className="self-start">
        <h2 className="text-[17px] font-bold">My watchlists</h2>
        {!wls ? <div className="mt-3"><Skeleton lines={2} /></div> : (
          <>
            {wls.length === 0 && <p className="mt-2 text-[13px] text-ink-3">Make your own list of stocks to test strategies on.</p>}
            <ul className="mt-2 divide-y divide-line">
              {wls.map((w) => (
                <li key={w.id}>
                  <Link href={`/lists/watchlist/${w.id}`} className="-mx-2 flex items-center justify-between rounded-lg px-2 py-3 hover:bg-card-2">
                    <div>
                      <div className="text-[15px] font-semibold">{w.name}</div>
                      <div className="text-[12px] text-ink-3">{w.items.length} stocks</div>
                    </div>
                    <span className="text-ink-3" aria-hidden>›</span>
                  </Link>
                </li>
              ))}
            </ul>
            <div className="mt-3 flex gap-2">
              <input value={name} onChange={(e) => setName(e.target.value)} placeholder="New list name"
                     className="min-w-0 flex-1 rounded-xl bg-card-2 px-3 text-[15px] outline-none" maxLength={100} />
              <Button onClick={create}>Create</Button>
            </div>
          </>
        )}
      </Card>
    </div>
  );
}
