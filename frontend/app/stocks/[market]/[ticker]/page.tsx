import { Suspense } from "react";
import { BackLink, Skeleton } from "@/components/ui";
import StockView from "./StockView";

export default function StockPage() {
  return (
    <>
      <BackLink href="/stocks">Search</BackLink>
      <Suspense fallback={<Skeleton lines={4} />}>
        <StockView />
      </Suspense>
    </>
  );
}
