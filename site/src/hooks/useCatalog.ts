import { useState } from "react";

export interface CatalogProduct {
  id: number;
  name: string;
  brand: string;
  category: string;
  categoryId: number;
  quantity: number;
  unit: string;
  prices: Record<string, number>;
  history: { date: string; ica?: number; coop?: number; willys?: number }[];
}

const BASE = import.meta.env.BASE_URL;

export function useCatalog() {
  const [catalog, setCatalog] = useState<CatalogProduct[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    if (catalog || loading) return;
    setLoading(true);
    fetch(`${BASE}data/catalog.json`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(setCatalog)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  return { catalog, loading, error, load };
}
