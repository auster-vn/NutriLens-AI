"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Heart, PackagePlus } from "lucide-react";
import { apiFetch, defaultProfile, type Product, type ProductScore, type ProductWithScore } from "@/lib/api";
import { ProductSummary } from "./ProductSummary";

export function ProductDetailPanel({ barcode }: { barcode: string }) {
  const [data, setData] = useState<ProductWithScore | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pantryMessage, setPantryMessage] = useState("");

  async function addToPantry() {
    if (!data) return;
    setError(null);
    setPantryMessage("");
    try {
      await apiFetch("/api/pantry", {
        method: "POST",
        body: JSON.stringify({
          barcode: data.product.barcode,
          quantity: 1,
          unit: "item",
          expiry_date: null,
          storage_location: "pantry"
        })
      });
      setPantryMessage("Added to pantry");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add product to pantry");
    }
  }

  async function addFavorite() {
    if (!data) return;
    setError(null);
    try {
      await apiFetch(`/api/favorites/${data.product.barcode}`, { method: "POST" });
      setPantryMessage("Saved to favorites");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save favorite");
    }
  }

  useEffect(() => {
    async function load() {
      try {
        const product = await apiFetch<Product>(`/api/products/${barcode}`);
        const score = await apiFetch<ProductScore>("/api/products/score", {
          method: "POST",
          body: JSON.stringify({
            nutriments: product.nutriments,
            allergens: product.allergens,
            additives: product.additives,
            nutriscore: product.nutriscore,
            ingredients_text: product.ingredients_text,
            user_profile: defaultProfile
          })
        });
        setData({ product, score });
      } catch (err) {
        setError(err instanceof Error ? err.message : "Product lookup failed");
      }
    }
    void load();
  }, [barcode]);

  return (
    <div className="page">
      <div>
        <p className="eyebrow">Product detail</p>
        <h1>Barcode {barcode}</h1>
      </div>
      {error ? <p className="error">{error}</p> : null}
      <section className="card toolbar">
        <button className="button" onClick={addToPantry} disabled={!data}><PackagePlus size={18} />Add to pantry</button>
        <button className="button secondary" onClick={addFavorite} disabled={!data}><Heart size={18} />Save favorite</button>
        <Link className="button secondary" href={`/compare?barcode=${barcode}`}>Compare with another</Link>
        <Link className="button secondary" href={`/chat?barcode=${barcode}`}>Ask about this product</Link>
        {pantryMessage ? <span className="badge">{pantryMessage}</span> : null}
      </section>
      {data ? <ProductSummary data={data} /> : <section className="card"><p className="muted">Loading product data...</p></section>}
    </div>
  );
}
