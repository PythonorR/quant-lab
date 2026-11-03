"use client";

import { useCallback, useEffect, useState } from "react";
import JobProgress from "@/components/JobProgress";
import { useJob } from "@/components/useJob";
import { Button } from "@/components/ui";
import { api, type CoverageSummary } from "@/lib/api/client";

/** Shows how much of a list's price history is stored, with a button to fetch the rest. */
export default function DownloadAll({ target }: { target: { universe?: string; watchlist_id?: number } }) {
  const [sum, setSum] = useState<CoverageSummary | null>(null);
  const refresh = useCallback(() => {
    api.coverage(target).then(setSum).catch(() => setSum(null));
  }, [target]);
  const { job, setJob, running, error, setError } = useJob(refresh);
  useEffect(refresh, [refresh]);

  if (!sum || sum.items.length === 0) return null;
  const total = sum.items.length;
  const stored = sum.ready + sum.incomplete;
  return (
    <div className="mt-3 rounded-xl bg-card-2 p-4">
      <div className="flex justify-between text-[14px]">
        <span className="text-ink-2">Price history stored</span>
        <span className="tabular font-semibold">{stored} / {total}</span>
      </div>
      {(sum.incomplete > 0 || sum.unavailable > 0) && (
        <p className="mt-1 text-[12px] text-warn">
          {sum.incomplete > 0 && `${sum.incomplete} with missing days. `}
          {sum.unavailable > 0 && `${sum.unavailable} with no data available.`}
        </p>
      )}
      {sum.needs_download > 0 && !running && (
        <Button className="mt-3 w-full" onClick={async () => {
          try { setError(null); setJob(await api.ensure(target)); } catch (e) { setError((e as Error).message); }
        }}>
          Download {sum.needs_download} missing
        </Button>
      )}
      {job && <JobProgress job={job} />}
      {error && <p className="mt-2 text-[13px] text-bad">{error}</p>}
    </div>
  );
}
