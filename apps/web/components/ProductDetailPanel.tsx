"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Heart, PackagePlus, MessageSquare, GitCompare, CheckCircle } from "lucide-react";
import {
  apiFetch,
  defaultProfile,
  toUserMessage,
  type Product,
  type ProductScore,
  type ProductWithScore,
} from "@/lib/api";
import { ProductSummary } from "./ProductSummary";

export function ProductDetailPanel({ barcode }: { barcode: string }) {
  const [data, setData] = useState<ProductWithScore | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [flash, setFlash] = useState<string | null>(null);

  function showFlash(msg: string) {
    setFlash(msg);
    setTimeout(() => setFlash(null), 3000);
  }

  async function addToPantry() {
    if (!data) return;
    setError(null);
    try {
      await apiFetch("/api/pantry", {
        method: "POST",
        body: JSON.stringify({
          barcode: data.product.barcode,
          quantity: 1,
          unit: "item",
          expiry_date: null,
          storage_location: "pantry",
        }),
      });
      showFlash("Đã thêm vào tủ đồ");
    } catch (err) {
      setError(toUserMessage(err, "Không thể thêm sản phẩm vào tủ đồ."));
    }
  }

  async function addFavorite() {
    if (!data) return;
    setError(null);
    try {
      await apiFetch(`/api/favorites/${data.product.barcode}`, { method: "POST" });
      showFlash("Đã lưu vào yêu thích");
    } catch (err) {
      setError(toUserMessage(err, "Không thể lưu sản phẩm yêu thích."));
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
            user_profile: defaultProfile,
          }),
        });
        setData({ product, score });
      } catch (err) {
        setError(toUserMessage(err, "Không thể tra cứu sản phẩm."));
      }
    }
    void load();
  }, [barcode]);

  return (
    <div className="page animate-slide-up">
      {/* Header */}
      <div className="header">
        <div>
          <p className="eyebrow">Chi tiết sản phẩm</p>
          <h1>{data?.product.name ?? `Mã vạch ${barcode}`}</h1>
          {data?.product.brand ? (
            <p className="muted">{data.product.brand} · {barcode}</p>
          ) : (
            <p className="muted">{barcode}</p>
          )}
        </div>
      </div>

      {/* Error */}
      {error ? <p className="error">{error}</p> : null}

      {/* Flash message */}
      {flash ? (
        <div
          style={{
            display: "flex", alignItems: "center", gap: 8, padding: "10px 16px",
            background: "var(--good-bg)", border: "1px solid rgba(16,185,129,0.25)",
            borderRadius: "var(--r)", color: "var(--good)", fontSize: 13.5, fontWeight: 600,
          }}
        >
          <CheckCircle size={16} />
          {flash}
        </div>
      ) : null}

      {/* Action toolbar */}
      <section className="card toolbar" style={{ gap: 10 }}>
        <button className="button" onClick={addToPantry} disabled={!data}>
          <PackagePlus size={15} />
          Thêm vào tủ đồ
        </button>
        <button className="button secondary" onClick={addFavorite} disabled={!data}>
          <Heart size={15} />
          Lưu yêu thích
        </button>
        <Link className="button secondary" href={`/compare?barcode=${barcode}`}>
          <GitCompare size={15} />
          So sánh
        </Link>
        <Link className="button secondary" href={`/chat?barcode=${barcode}`}>
          <MessageSquare size={15} />
          Hỏi AI
        </Link>
      </section>

      {/* Product data */}
      {data ? (
        <ProductSummary data={data} />
      ) : !error ? (
        <section className="card">
          <div className="loading-state" style={{ minHeight: 120 }}>
            Đang tải dữ liệu sản phẩm…
          </div>
        </section>
      ) : null}
    </div>
  );
}
