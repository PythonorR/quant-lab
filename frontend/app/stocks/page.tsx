import { Suspense } from "react";
import { PageTitle, Skeleton } from "@/components/ui";
import StocksView from "./StocksView";

export default function StocksPage() {
  return (
    <div className="mx-auto max-w-3xl">
      <PageTitle sub="Search every Korean and US stock by name or ticker. Currently listed stocks only.">Find a stock</PageTitle>
      <Suspense fallback={<Skeleton lines={2} />}>
        <StocksView />
      </Suspense>
    </div>
  );
}
