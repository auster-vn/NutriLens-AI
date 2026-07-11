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
    <div className="page animate-slide-up">
      <div className="header">
        <div>
          <p className="eyebrow">Sản phẩm đã lưu</p>
          <h1>Yêu thích của tôi</h1>
          <p className="muted">Lưu sản phẩm bạn muốn so sánh hoặc mua lại.</p>
        </div>
        <Link className="button" href="/scan">
          <ScanLine size={16} />
          Tìm sản phẩm
        </Link>
      </div>

      {error ? <p className="error">{error}</p> : null}

      {products.length ? (
        <section className="product-grid">
          {products.map((product) => (
            <article className="product-card" key={product.barcode}>
              <Link href={`/product/${product.barcode}`}>
                <div className="product-image">
                  {product.image_url ? (
                    <Image
                      src={product.image_url}
                      alt={product.name ?? product.barcode}
                      width={150}
                      height={150}
                    />
                  ) : (
                    <span className="muted" style={{ fontSize: 12 }}>Không có ảnh</span>
                  )}
                </div>
                <span className="badge" style={{ marginBottom: 8 }}>
                  {product.nutriscore
                    ? `Nutri-Score ${product.nutriscore.toUpperCase()}`
                    : "Chưa xếp hạng"}
                </span>
                <h2>{product.name ?? product.barcode}</h2>
                <p className="muted">{product.brand ?? "Thương hiệu chưa xác định"}</p>
              </Link>
              <button
                className="icon-button"
                title="Xóa khỏi yêu thích"
                onClick={() => void remove(product.barcode)}
              >
                <HeartOff size={15} />
              </button>
            </article>
          ))}
        </section>
      ) : (
        <section className="card empty-state" style={{ minHeight: 200 }}>
          <div style={{ textAlign: "center" }}>
            <HeartOff size={36} strokeWidth={1.2} style={{ marginBottom: 10, opacity: 0.3, color: "var(--muted)" }} />
            <p style={{ margin: 0, fontWeight: 600 }}>Chưa có sản phẩm yêu thích</p>
            <p className="muted" style={{ margin: "4px 0 0", fontSize: 13 }}>
              Lưu từ trang chi tiết sản phẩm.
            </p>
          </div>
        </section>
      )}
    </div>
  );
}
