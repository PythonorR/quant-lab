"use client";

import { useRouter, useSearchParams } from "next/navigation";
import StockSearch from "@/components/StockSearch";

export default function StocksView() {
  const params = useSearchParams();
  const router = useRouter();
  return (
    <StockSearch
      autoFocus
      initialQuery={params.get("q") ?? ""}
      // Keep the query in the URL so Back returns to the same results.
      onQueryChange={(q) => router.replace(q ? `/stocks?q=${encodeURIComponent(q)}` : "/stocks", { scroll: false })}
    />
  );
}
