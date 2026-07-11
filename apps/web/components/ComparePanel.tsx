"use client";

import { useEffect, useState } from "react";
import { GitCompare } from "lucide-react";
import { apiFetch, defaultProfile, type ProductWithScore } from "@/lib/api";
import { NutritionChart } from "./NutritionChart";
import { ProductSummary } from "./ProductSummary";

type CompareResult = {
  product_a: ProductWithScore;
  product_b: ProductWithScore;
  recommendation: string;
  dimensions: Array<{ key: string; label: string; a: number | null; b: number | null }>;
};

export function ComparePanel() {
  const [barcodeA, setBarcodeA] = useState("737628064502");
  const [barcodeB, setBarcodeB] = useState("3017620422003");
  const [goal, setGoal] = useState("low_sugar");
  const [result, setResult] = useState<CompareResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const linkedBarcode = params.get("barcode");
    if (linkedBarcode) {
      // Hydrate optional deep-link state from the current URL.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setBarcodeA(linkedBarcode);
    }
  }, []);

  async function compare() {
    setLoading(true);
    setError(null);
    try {
      setResult(await apiFetch<CompareResult>("/api/products/compare", {
        method: "POST",
        body: JSON.stringify({ barcode_a: barcodeA, barcode_b: barcodeB, user_profile: { ...defaultProfile, goal } })
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Compare failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page animate-slide-up">
      <div className="header">
        <div>
          <p className="eyebrow">So sánh sản phẩm</p>
          <h1>Chọn sản phẩm phù hợp hơn</h1>
          <p className="muted">Khuyến nghị thay đổi theo mục tiêu, trong khi giá trị dinh dưỡng luôn hiển thị.</p>
        </div>
      </div>
      <section className="card">
        <div className="toolbar" style={{ gap: 12 }}>
          <label className="field" style={{ flex: "1 1 180px" }}>
            <span>Mã vạch sản phẩm A</span>
            <input value={barcodeA} onChange={(e) => setBarcodeA(e.target.value)} placeholder="e.g. 737628064502" />
          </label>
          <label className="field" style={{ flex: "1 1 180px" }}>
            <span>Mã vạch sản phẩm B</span>
            <input value={barcodeB} onChange={(e) => setBarcodeB(e.target.value)} placeholder="e.g. 3017620422003" />
          </label>
          <label className="field" style={{ flex: "0 1 180px" }}>
            <span>Mục tiêu</span>
            <select value={goal} onChange={(e) => setGoal(e.target.value)}>
              <option value="low_sugar">Ít đường</option>
              <option value="low_sodium">Ít natri</option>
              <option value="high_protein">Nhiều protein</option>
              <option value="weight_loss">Giảm cân</option>
              <option value="general">Tổng quát</option>
            </select>
          </label>
          <button className="button" onClick={compare} disabled={loading} style={{ alignSelf: "flex-end" }}>
            <GitCompare size={16} />
            {loading ? "Đang so sánh…" : "So sánh"}
          </button>
        </div>
        {error ? <p className="error" style={{ marginTop: 10 }}>{error}</p> : null}
      </section>

      {result ? (
        <>
          <section className="card">
            <p className="eyebrow">Phân tích AI</p>
            <h2 style={{ marginBottom: 8 }}>Khuyến nghị</h2>
            <p style={{ fontSize: 14, lineHeight: 1.7, color: "var(--ink-2)" }}>{result.recommendation}</p>
            <div style={{ marginTop: 16 }}>
              <NutritionChart
                data={result.dimensions.map((row) => ({ label: row.label, a: row.a, b: row.b }))}
                mode="compare"
              />
            </div>
            <table className="table" style={{ marginTop: 16 }}>
              <thead>
                <tr>
                  <th>Chỉ số</th>
                  <th>Sản phẩm A</th>
                  <th>Sản phẩm B</th>
                </tr>
              </thead>
              <tbody>
                {result.dimensions.map((row) => (
                  <tr key={row.key}>
                    <td style={{ fontWeight: 500 }}>{row.label}</td>
                    <td style={{ fontWeight: 600 }}>{row.a ?? <span className="muted">–</span>}</td>
                    <td style={{ fontWeight: 600 }}>{row.b ?? <span className="muted">–</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
          <div className="grid two">
            <div>
              <p className="eyebrow" style={{ marginBottom: 8 }}>Sản phẩm A</p>
              <ProductSummary data={result.product_a} />
            </div>
            <div>
              <p className="eyebrow" style={{ marginBottom: 8 }}>Sản phẩm B</p>
              <ProductSummary data={result.product_b} />
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}
