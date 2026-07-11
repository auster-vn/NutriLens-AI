"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { useAuth } from "./AuthProvider";

type ScanHistoryItem = {
  id: string;
  barcode: string;
  score?: number | null;
  created_at: string;
  product_name?: string | null;
  brand?: string | null;
  image_url?: string | null;
};

export function ScanHistoryPanel({ refreshKey = 0 }: { refreshKey?: number }) {
  const { user } = useAuth();
  const [items, setItems] = useState<ScanHistoryItem[]>([]);

  async function load() {
    setItems(await apiFetch<ScanHistoryItem[]>("/api/scan/history"));
  }

  useEffect(() => {
    if (!user) return;
    // Initial client-side fetch for recent scans.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load().catch(() => undefined);
  }, [refreshKey, user]);

  if (!user) {
    return <section className="card empty-state">Sign in to keep a private scan history and build dashboard insights.</section>;
  }

  return (
    <section className="card">
      <div className="toolbar" style={{ justifyContent: "space-between" }}>
        <h2>Recent scans</h2>
        <button className="button secondary" onClick={load}><RefreshCw size={16} />Refresh</button>
      </div>
      <ul className="list">
        {items.map((item) => (
          <li key={item.id}>
            <Link className="product-cell" href={`/product/${item.barcode}`}>
              {item.image_url ? <Image src={item.image_url} alt={item.product_name ?? item.barcode} width={42} height={42} /> : <div className="thumb-placeholder" />}
              <span>
                <strong>{item.product_name ?? item.barcode}</strong>
                <span className="muted">{item.brand ?? item.barcode} · score {item.score ?? "n/a"}</span>
              </span>
            </Link>
          </li>
        ))}
        {!items.length ? <li className="muted">No scans yet.</li> : null}
      </ul>
    </section>
  );
}
