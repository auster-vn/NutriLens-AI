"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";
import { HeartOff, ScanLine } from "lucide-react";
import { apiFetch, type Product } from "@/lib/api";

export function FavoritesPanel() {
  const [products, setProducts] = useState<Product[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setProducts(await apiFetch<Product[]>("/api/favorites"));
  }

  useEffect(() => {
    // Initial client-side fetch for the signed-in user's favorites.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load().catch((err) => setError(err instanceof Error ? err.message : "Favorites failed"));
  }, []);

  async function remove(barcode: string) {
    try {
      await apiFetch<void>(`/api/favorites/${barcode}`, { method: "DELETE" });
      setProducts((current) => current.filter((product) => product.barcode !== barcode));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not remove favorite");
    }
  }

  return (
    <div className="page">
      <div className="header"><div><p className="eyebrow">Saved products</p><h1>Favorites</h1><p className="muted">Keep products you want to compare or buy again.</p></div><Link className="button" href="/scan"><ScanLine size={18} />Find products</Link></div>
      {error ? <p className="error">{error}</p> : null}
      <section className="product-grid">
        {products.map((product) => (
          <article className="product-card" key={product.barcode}>
            <Link href={`/product/${product.barcode}`}>
              <div className="product-image">{product.image_url ? <Image src={product.image_url} alt={product.name ?? product.barcode} width={150} height={150} /> : <span>No image</span>}</div>
              <span className="badge">{product.nutriscore ? `Nutri-Score ${product.nutriscore.toUpperCase()}` : "Unrated"}</span>
              <h2>{product.name ?? product.barcode}</h2><p className="muted">{product.brand ?? "Unknown brand"}</p>
            </Link>
            <button className="icon-button" title="Remove favorite" onClick={() => void remove(product.barcode)}><HeartOff size={18} /></button>
          </article>
        ))}
      </section>
      {!products.length ? <section className="empty-state card">No favorites yet. Save one from a product detail page.</section> : null}
    </div>
  );
}
