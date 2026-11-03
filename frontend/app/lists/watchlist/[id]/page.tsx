import { Suspense } from "react";
import { BackLink, Skeleton } from "@/components/ui";
import WatchlistView from "./WatchlistView";

export default function WatchlistPage() {
  return (
    <>
      <BackLink href="/lists">Lists</BackLink>
      <Suspense fallback={<Skeleton lines={4} />}>
        <WatchlistView />
      </Suspense>
    </>
  );
}
