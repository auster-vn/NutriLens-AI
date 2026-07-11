"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import { Plus, Trash2 } from "lucide-react";
import { apiFetch } from "@/lib/api";

type PantryItem = {
  id: string;
  user_id: string;
  barcode: string;
  quantity?: number | null;
  unit?: string | null;
  expiry_date?: string | null;
  storage_location?: string | null;
  product_name?: string | null;
  brand?: string | null;
  image_url?: string | null;
  expiry_status: "expired" | "urgent" | "soon" | "ok" | "unknown";
};

export function PantryPanel() {
  const [items, setItems] = useState<PantryItem[]>([]);
  const [form, setForm] = useState({ barcode: "737628064502", quantity: "1", unit: "pack", expiry_date: "", storage_location: "pantry" });
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setItems(await apiFetch<PantryItem[]>("/api/pantry"));
  }

  useEffect(() => {
    // Initial client-side fetch for the demo pantry list.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load().catch(() => undefined);
  }, []);

  async function add() {
    setError(null);
    try {
      await apiFetch<PantryItem>("/api/pantry", {
        method: "POST",
        body: JSON.stringify({ ...form, quantity: Number(form.quantity), expiry_date: form.expiry_date || null })
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Add failed");
    }
  }

  async function remove(id: string) {
    setError(null);
    try {
      await apiFetch<void>(`/api/pantry/${id}`, { method: "DELETE" });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    }
  }

  return (
    <div className="page">
      <div>
        <p className="eyebrow">Pantry tracker</p>
        <h1>Track products at home</h1>
      </div>
      <section className="card toolbar">
        <label className="field"><span>Barcode</span><input value={form.barcode} onChange={(event) => setForm({ ...form, barcode: event.target.value })} /></label>
        <label className="field"><span>Qty</span><input value={form.quantity} onChange={(event) => setForm({ ...form, quantity: event.target.value })} /></label>
        <label className="field"><span>Unit</span><input value={form.unit} onChange={(event) => setForm({ ...form, unit: event.target.value })} /></label>
        <label className="field"><span>Expiry</span><input type="date" value={form.expiry_date} onChange={(event) => setForm({ ...form, expiry_date: event.target.value })} /></label>
        <label className="field"><span>Location</span><select value={form.storage_location} onChange={(event) => setForm({ ...form, storage_location: event.target.value })}><option>pantry</option><option>fridge</option><option>freezer</option></select></label>
        <button className="button" onClick={add}><Plus size={18} />Add</button>
      </section>
      {error ? <p className="error">{error}</p> : null}
      <section className="card">
        <table className="table">
          <thead><tr><th>Product</th><th>Qty</th><th>Expiry</th><th>Location</th><th></th></tr></thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id}>
                <td>
                  <div className="product-cell">
                    {item.image_url ? <Image src={item.image_url} alt={item.product_name ?? item.barcode} width={42} height={42} /> : <div className="thumb-placeholder" />}
                    <div>
                      <strong>{item.product_name ?? item.barcode}</strong>
                      <p className="muted">{item.brand ?? item.barcode}</p>
                    </div>
                  </div>
                </td>
                <td>{item.quantity} {item.unit}</td>
                <td><span className={`badge expiry-${item.expiry_status}`}>{item.expiry_date ?? "Not set"}</span></td>
                <td>{item.storage_location}</td>
                <td><button className="button secondary" onClick={() => remove(item.id)} title="Delete"><Trash2 size={16} /></button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
