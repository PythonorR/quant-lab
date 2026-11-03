// Thin typed wrapper over fetch. Types come from the backend's OpenAPI schema (npm run gen:api).
import type { components } from "./schema";

export type Schemas = components["schemas"];
export type Instrument = Schemas["InstrumentOut"];
export type Coverage = Schemas["CoverageOut"];
export type StockDetail = Schemas["StockDetailOut"];
export type Prices = Schemas["PricesOut"];
export type Job = Schemas["JobOut"];
export type Universe = Schemas["UniverseOut"];
export type UniverseMembers = Schemas["UniverseMembersOut"];
export type Watchlist = Schemas["WatchlistOut"];
export type CoverageSummary = Schemas["CoverageSummaryOut"];

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
      cache: "no-store",
    });
  } catch {
    throw new ApiError(0, "Can't reach the QuantLab server. Is the backend running?");
  }
  if (!res.ok) {
    let msg = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") msg = body.detail;
    } catch {}
    throw new ApiError(res.status, msg);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

const qs = (p: Record<string, string | number | undefined | null>) => {
  const s = new URLSearchParams();
  for (const [k, v] of Object.entries(p)) if (v !== undefined && v !== null && v !== "") s.set(k, String(v));
  const out = s.toString();
  return out ? `?${out}` : "";
};

export const api = {
  search: (q: string, market?: string) =>
    request<Instrument[]>(`/api/stocks/search${qs({ q, market, limit: 20 })}`),
  stock: (market: string, ticker: string, start?: string) =>
    request<StockDetail>(`/api/stocks/${market}/${encodeURIComponent(ticker)}${qs({ start })}`),
  prices: (market: string, ticker: string, start?: string) =>
    request<Prices>(`/api/stocks/${market}/${encodeURIComponent(ticker)}/prices${qs({ start })}`),
  ensure: (body: Schemas["EnsureRequest"]) =>
    request<Job>(`/api/data/ensure`, { method: "POST", body: JSON.stringify(body) }),
  coverage: (body: Schemas["CoverageRequest"]) =>
    request<CoverageSummary>(`/api/data/coverage`, { method: "POST", body: JSON.stringify(body) }),
  job: (id: number) => request<Job>(`/api/data/jobs/${id}`),
  universes: () => request<Universe[]>(`/api/universes`),
  members: (code: string, date?: string) => request<UniverseMembers>(`/api/universes/${code}/members${qs({ date })}`),
  watchlists: () => request<Watchlist[]>(`/api/watchlists`),
  watchlist: (id: number) => request<Watchlist>(`/api/watchlists/${id}`),
  createWatchlist: (name: string) =>
    request<Watchlist>(`/api/watchlists`, { method: "POST", body: JSON.stringify({ name }) }),
  deleteWatchlist: (id: number) => request<void>(`/api/watchlists/${id}`, { method: "DELETE" }),
  addToWatchlist: (id: number, instrument_id: number) =>
    request<Watchlist>(`/api/watchlists/${id}/items`, { method: "POST", body: JSON.stringify({ instrument_id }) }),
  removeFromWatchlist: (id: number, instrument_id: number) =>
    request<Watchlist>(`/api/watchlists/${id}/items/${instrument_id}`, { method: "DELETE" }),
};
