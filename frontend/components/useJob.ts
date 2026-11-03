"use client";

import { useEffect, useState } from "react";
import { api, type Job } from "@/lib/api/client";

/** Polls a download job until it finishes. */
export function useJob(onFinished?: (job: Job) => void) {
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!job || job.status === "done" || job.status === "failed") return;
    const t = setTimeout(() => {
      api.job(job.id)
        .then((j) => {
          setJob(j);
          if (j.status === "done" || j.status === "failed") onFinished?.(j);
        })
        .catch((e) => setError(e.message));
    }, 1000);
    return () => clearTimeout(t);
  }, [job, onFinished]);

  const running = !!job && (job.status === "queued" || job.status === "running");
  return { job, setJob, running, error, setError };
}
