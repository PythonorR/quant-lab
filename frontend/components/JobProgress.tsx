import type { Job } from "@/lib/api/client";
import { Notice } from "./ui";

export default function JobProgress({ job }: { job: Job }) {
  const pct = job.total ? Math.round((job.done / job.total) * 100) : 0;
  if (job.status === "queued" || job.status === "running") {
    return (
      <div className="mt-3">
        <div className="mb-1.5 flex justify-between text-[13px] text-ink-2">
          <span>Downloading price history…</span>
          <span className="tabular">{job.done} / {job.total}</span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-card-2">
          <div className="h-full rounded-full bg-brand transition-all" style={{ width: `${pct}%` }} />
        </div>
      </div>
    );
  }
  const failed = job.failures?.length ?? 0;
  return (
    <div className="mt-3">
      <Notice tone={job.status === "failed" || failed ? "warn" : "good"}>
        {job.message ?? (job.status === "failed" ? "The download failed." : "Done.")}
        {failed > 0 && (
          <details className="mt-1">
            <summary className="cursor-pointer">Show which stocks</summary>
            <ul className="mt-1 space-y-1">
              {job.failures.map((f, k) => (
                <li key={k} className="break-words text-[12px]"><b>{String(f.ticker)}</b>: {String(f.message ?? f.outcome)}</li>
              ))}
            </ul>
          </details>
        )}
      </Notice>
    </div>
  );
}
