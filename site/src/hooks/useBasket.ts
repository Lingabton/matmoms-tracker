import { useState, useEffect } from "react";

export interface BasketItem {
  productId: number;
  name: string;
  brand: string;
  prices: Record<string, number>;
  qty: number;
}

const STORAGE_KEY = "matmoms-basket";

function readStorage(): BasketItem[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (item: unknown): item is BasketItem =>
        typeof item === "object" && item !== null &&
        typeof (item as BasketItem).productId === "number" &&
        typeof (item as BasketItem).name === "string" &&
        typeof (item as BasketItem).brand === "string" &&
        typeof (item as BasketItem).qty === "number" &&
        (item as BasketItem).qty > 0 &&
        typeof (item as BasketItem).prices === "object"
    );
  } catch {
    return [];
  }
}

export function useBasket() {
  const [items, setItems] = useState<BasketItem[]>(readStorage);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  }, [items]);

  const add = (product: { id: number; name: string; brand: string; prices: Record<string, number> }) => {
    setItems((prev) => {
      const existing = prev.find((i) => i.productId === product.id);
      if (existing) {
        return prev.map((i) =>
          i.productId === product.id ? { ...i, qty: i.qty + 1 } : i
        );
      }
      return [...prev, { productId: product.id, name: product.name, brand: product.brand, prices: product.prices, qty: 1 }];
    });
  };

  const remove = (productId: number) => {
    setItems((prev) => prev.filter((i) => i.productId !== productId));
  };

  const updateQty = (productId: number, qty: number) => {
    if (qty <= 0) return remove(productId);
    setItems((prev) =>
      prev.map((i) => (i.productId === productId ? { ...i, qty } : i))
    );
  };

  const clear = () => setItems([]);

  const totals = () => {
    const chains = ["ica", "coop", "willys"] as const;
    const result: Record<string, number | null> = {};
    for (const chain of chains) {
      let total = 0;
      let allHave = true;
      for (const item of items) {
        const p = item.prices[chain];
        if (p == null) {
          allHave = false;
          break;
        }
        total += p * item.qty;
      }
      result[chain] = allHave ? Math.round(total * 100) / 100 : null;
    }
    return result;
  };

  return { items, add, remove, updateQty, clear, totals, count: items.reduce((s, i) => s + i.qty, 0) };
}
