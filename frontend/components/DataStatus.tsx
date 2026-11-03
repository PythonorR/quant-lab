"use client";

import { useCallback } from "react";
import { api, type Coverage, type Instrument } from "@/lib/api/client";
import { ADJUSTMENT_LABEL, formatDate } from "@/lib/format";
import JobProgress from "./JobProgress";
import { useJob } from "./useJob";
import { Badge, Button, Card, PanelTitle } from "./ui";

const STATUS = {
  ready: { tone: "good", label: "Ready", title: "Price history is stored" },
  incomplete: { tone: "warn", label: "Incomplete", title: "Some trading days are missing" },
  needs_download: { tone: "neutral", label: "Not downloaded", title: "Price history not downloaded yet" },
  unavailable: { tone: "bad", label: "Unavailable", title: "No price data available" },
} as const;

export default function DataStatus({
  instrument, coverage, onUpdated,
}: { instrument: Instrument; coverage: Coverage; onUpdated: () => void }) {
  const { job, setJob, running, error, setError } = useJob(useCallback(() => onUpdated(), [onUpdated]));
  // Some data is stored but newer trading days are not yet: an update, not a first download.
  const stale = coverage.status === "needs_download" && !!coverage.last_bar;
  const s = stale
    ? ({ tone: "warn", label: "Out of date", title: "Newer prices are available" } as const)
    : STATUS[coverage.status as keyof typeof STATUS] ?? STATUS.needs_download;
  const failedBefore = coverage.notes.find((n) => n.startsWith("Download failed"));

  const download = async () => {
    try {
      setError(null);
      setJob(await api.ensure({ instrument_ids: [instrument.id] }));
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <Card>
      <PanelTitle right={<Badge tone={s.tone}>{s.label}</Badge>}>Price data</PanelTitle>
      <p className="text-[14px] font-semibold">{s.title}</p>

      {coverage.first_bar && coverage.last_bar && (
        <dl className="tabular mt-3 grid grid-cols-2 gap-y-2 text-[14px]">
          <dt className="text-ink-3">From</dt>
          <dd className="text-right font-semibold">{formatDate(coverage.first_bar)}</dd>
          <dt className="text-ink-3">To</dt>
          <dd className="text-right font-semibold">{formatDate(coverage.last_bar)}</dd>
          {coverage.bars > 0 && (
            <>
              <dt className="text-ink-3">Trading days</dt>
              <dd className="text-right font-semibold">{coverage.bars.toLocaleString()}</dd>
            </>
          )}
          {coverage.missing_count > 0 && (
            <>
              <dt className="text-ink-3">Missing days</dt>
              <dd className="text-right font-semibold text-warn">{coverage.missing_count}</dd>
            </>
          )}
          <dt className="text-ink-3">Prices</dt>
          <dd className="text-right">{ADJUSTMENT_LABEL[coverage.adjustment ?? ""] ?? "—"}</dd>
          <dt className="text-ink-3">Source</dt>
          <dd className="text-right">{coverage.provider ?? "—"}</dd>
        </dl>
      )}

      {coverage.status === "needs_download" && !stale && !running && (
        <p className="mt-2 text-[13px] text-ink-3">
          {failedBefore ? "The last download attempt failed. You can try again." :
            "Download the daily price history once; after that it's read from QuantLab's own database."}
        </p>
      )}
      {coverage.status === "unavailable" && (
        <p className="mt-2 text-[13px] text-ink-3">None of the data sources has prices for this stock.</p>
      )}

      {coverage.notes.length > 0 && (
        <details className="mt-3 text-[12px] text-ink-3">
          <summary className="cursor-pointer">Details</summary>
          <ul className="mt-1 list-disc space-y-1 pl-4">
            {coverage.notes.map((n, k) => <li key={k} className="break-words">{n}</li>)}
            {coverage.missing_dates.length > 0 && (
              <li>Missing: {coverage.missing_dates.join(", ")}{coverage.missing_count > coverage.missing_dates.length ? " …" : ""}</li>
            )}
          </ul>
        </details>
      )}

      {coverage.status === "needs_download" && !running && (
        <Button className="mt-4 w-full" onClick={download}>
          {failedBefore ? "Try again" : stale ? "Update prices" : "Download price history"}
        </Button>
      )}
      {job && <JobProgress job={job} />}
      {error && <p className="mt-2 text-[13px] text-bad">{error}</p>}
    </Card>
  );
}
