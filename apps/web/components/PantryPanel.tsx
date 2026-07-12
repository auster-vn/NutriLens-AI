"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import { Plus, Trash2, Package, RefreshCw } from "lucide-react";
import { apiFetch, toUserMessage } from "@/lib/api";

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

const expiryLabel: Record<string, string> = {
  expired: "Hết hạn",
  urgent:  "Sắp hết",
  soon:    "Gần hết",
  ok:      "Còn hạn",
  unknown: "Chưa đặt",
};

const storageOptions = ["pantry", "fridge", "freezer"];
const storageLabel: Record<string, string> = {
  pantry:  "Tủ bếp",
  fridge:  "Tủ lạnh",
  freezer: "Ngăn đông",
};

export function PantryPanel() {
  const [items, setItems] = useState<PantryItem[]>([]);
  const [form, setForm] = useState({
    barcode: "737628064502",
    quantity: "1",
    unit: "pack",
    expiry_date: "",
    storage_location: "pantry",
  });
  const [error, setError] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);

  async function load() {
    setItems(await apiFetch<PantryItem[]>("/api/pantry"));
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load().catch(() => undefined);
  }, []);

  async function add() {
    setError(null);
    setAdding(true);
    try {
      await apiFetch<PantryItem>("/api/pantry", {
        method: "POST",
        body: JSON.stringify({
          ...form,
          quantity: Number(form.quantity),
          expiry_date: form.expiry_date || null,
        }),
      });
      await load();
    } catch (err) {
      setError(toUserMessage(err, "Không thể thêm sản phẩm vào tủ đồ."));
    } finally {
      setAdding(false);
    }
  }

  async function remove(id: string) {
    setError(null);
    try {
      await apiFetch<void>(`/api/pantry/${id}`, { method: "DELETE" });
      await load();
    } catch (err) {
      setError(toUserMessage(err, "Không thể xóa sản phẩm khỏi tủ đồ."));
    }
  }

  return (
    <div className="page animate-slide-up">
      {/* Header */}
      <div className="header">
        <div>
          <p className="eyebrow">Theo dõi thực phẩm</p>
          <h1>Tủ đồ của tôi</h1>
          <p className="muted">Quản lý thực phẩm tại nhà, kiểm tra hạn sử dụng và vị trí lưu trữ.</p>
        </div>
        <button className="button secondary" onClick={load} title="Làm mới">
          <RefreshCw size={15} />
          Làm mới
        </button>
      </div>

      {/* Add form */}
      <section className="card">
        <h2 style={{ marginBottom: 14 }}>Thêm sản phẩm</h2>
        <div className="toolbar" style={{ alignItems: "flex-end", gap: 12 }}>
          <label className="field" style={{ flex: "2 1 160px" }}>
            <span>Mã vạch</span>
            <input
              value={form.barcode}
              onChange={(e) => setForm({ ...form, barcode: e.target.value })}
              placeholder="e.g. 737628064502"
            />
          </label>
          <label className="field" style={{ flex: "0 1 80px" }}>
            <span>Số lượng</span>
            <input
              type="number"
              min={1}
              value={form.quantity}
              onChange={(e) => setForm({ ...form, quantity: e.target.value })}
            />
          </label>
          <label className="field" style={{ flex: "1 1 80px" }}>
            <span>Đơn vị</span>
            <input
              value={form.unit}
              onChange={(e) => setForm({ ...form, unit: e.target.value })}
              placeholder="pack"
            />
          </label>
          <label className="field" style={{ flex: "1 1 120px" }}>
            <span>Hạn dùng</span>
            <input
              type="date"
              value={form.expiry_date}
              onChange={(e) => setForm({ ...form, expiry_date: e.target.value })}
            />
          </label>
          <label className="field" style={{ flex: "1 1 100px" }}>
            <span>Vị trí</span>
            <select
              value={form.storage_location}
              onChange={(e) => setForm({ ...form, storage_location: e.target.value })}
            >
              {storageOptions.map((opt) => (
                <option key={opt} value={opt}>{storageLabel[opt]}</option>
              ))}
            </select>
          </label>
          <button
            className="button"
            onClick={add}
            disabled={adding}
            style={{ alignSelf: "flex-end" }}
          >
            <Plus size={16} />
            {adding ? "Đang thêm…" : "Thêm"}
          </button>
        </div>
        {error ? <p className="error" style={{ marginTop: 10 }}>{error}</p> : null}
      </section>

      {/* Items table */}
      <section className="card" style={{ padding: 0, overflow: "hidden" }}>
        {items.length === 0 ? (
          <div className="empty-state" style={{ minHeight: 180 }}>
            <Package size={36} strokeWidth={1.2} style={{ marginBottom: 10, opacity: 0.35 }} />
            <p style={{ margin: 0, fontWeight: 600 }}>Tủ đồ trống</p>
            <p className="muted" style={{ margin: "4px 0 0", fontSize: 13 }}>
              Thêm sản phẩm đầu tiên của bạn ở trên.
            </p>
          </div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Sản phẩm</th>
                <th>Số lượng</th>
                <th>Hạn dùng</th>
                <th>Vị trí</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <td>
                    <div className="product-cell">
                      {item.image_url ? (
                        <Image
                          src={item.image_url}
                          alt={item.product_name ?? item.barcode}
                          width={40}
                          height={40}
                          style={{ borderRadius: "var(--r-sm)", objectFit: "contain" }}
                        />
                      ) : (
                        <div className="thumb-placeholder" />
                      )}
                      <div>
                        <strong style={{ fontSize: 13.5 }}>
                          {item.product_name ?? item.barcode}
                        </strong>
                        <p className="muted" style={{ margin: 0, fontSize: 12 }}>
                          {item.brand ?? item.barcode}
                        </p>
                      </div>
                    </div>
                  </td>
                  <td style={{ fontWeight: 600, fontSize: 13.5 }}>
                    {item.quantity} {item.unit}
                  </td>
                  <td>
                    <span className={`badge expiry-${item.expiry_status}`}>
                      {expiryLabel[item.expiry_status] ?? item.expiry_status}
                      {item.expiry_date ? ` · ${item.expiry_date}` : ""}
                    </span>
                  </td>
                  <td style={{ color: "var(--ink-2)", fontSize: 13 }}>
                    {storageLabel[item.storage_location ?? ""] ?? item.storage_location}
                  </td>
                  <td>
                    <button
                      className="icon-button"
                      onClick={() => remove(item.id)}
                      title="Xóa"
                    >
                      <Trash2 size={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
