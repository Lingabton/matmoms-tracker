import { useEffect, useState } from "react";

export interface SiteData {
  generatedAt: string;
  vatCutDate: string;
  isPostCut: boolean;
  expectedDropPercent: number;
  summary: {
    totalObservations: number;
    foundObservations: number;
    totalProducts: number;
    totalStores: number;
    totalChains: number;
    daysOfData: number;
    passThroughPercent?: number;
  };
  baseline: {
    daily: { date: string; total: number; found: number }[];
    coveragePercent: number;
    uniqueProductStores: number;
    totalProductStores: number;
  };
  byChain: {
    chain: string;
    chainName: string;
    observations: number;
    found: number;
    hitRate: number;
    avgPrice: number | null;
    stores: number;
    passThroughPercent?: number;
  }[];
  byCategory: {
    category: string;
    categoryId: string;
    observations: number;
    found: number;
    hitRate: number;
    avgPrice: number | null;
    passThroughPercent?: number;
  }[];
  byCity: {
    city: string;
    observations: number;
    found: number;
    hitRate: number;
    avgPrice: number | null;
    stores: number;
  }[];
  timeline: {
    date: string;
    chain: string;
    observations: number;
    found: number;
    avgPrice: number | null;
  }[];
  products: {
    productId: number;
    name: string;
    brand: string;
    category: string;
    quantity: number;
    unit: string;
    chain: string;
    store: string;
    city: string;
    price: number;
    unitPrice: number | null;
    isCampaign: boolean;
    observedAt: string;
  }[];
}

const BASE = import.meta.env.BASE_URL;

export function useData() {
  const [data, setData] = useState<SiteData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${BASE}data/latest.json`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return { data, loading, error };
}
