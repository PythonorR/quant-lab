import { Suspense } from "react";
import { BackLink, Skeleton } from "@/components/ui";
import UniverseView from "./UniverseView";

export default function UniversePage() {
  return (
    <>
      <BackLink href="/lists">Lists</BackLink>
      <Suspense fallback={<Skeleton lines={5} />}>
        <UniverseView />
      </Suspense>
    </>
  );
}
