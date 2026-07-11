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
    <div className="page">
      <div>
        <p className="eyebrow">Product comparison</p>
        <h1>Choose the better fit</h1>
        <p className="muted">Recommendation changes by goal, while raw nutrition values stay visible.</p>
      </div>
      <section className="card toolbar">
        <label className="field" style={{ flex: "1 1 180px" }}><span>Product A barcode</span><input value={barcodeA} onChange={(event) => setBarcodeA(event.target.value)} /></label>
        <label className="field" style={{ flex: "1 1 180px" }}><span>Product B barcode</span><input value={barcodeB} onChange={(event) => setBarcodeB(event.target.value)} /></label>
        <label className="field" style={{ flex: "0 1 180px" }}><span>Goal</span><select value={goal} onChange={(event) => setGoal(event.target.value)}><option value="low_sugar">Low sugar</option><option value="low_sodium">Low sodium</option><option value="high_protein">High protein</option><option value="weight_loss">Weight loss</option><option value="general">General</option></select></label>
        <button className="button" onClick={compare} disabled={loading}><GitCompare size={18} />{loading ? "Comparing" : "Compare"}</button>
      </section>
      {error ? <p className="error">{error}</p> : null}
      {result ? (
        <>
          <section className="card">
            <h2>Recommendation</h2>
            <p>{result.recommendation}</p>
            <NutritionChart data={result.dimensions.map((row) => ({ label: row.label, a: row.a, b: row.b }))} mode="compare" />
            <table className="table">
              <thead><tr><th>Dimension</th><th>A</th><th>B</th></tr></thead>
              <tbody>{result.dimensions.map((row) => <tr key={row.key}><td>{row.label}</td><td>{row.a ?? "Missing"}</td><td>{row.b ?? "Missing"}</td></tr>)}</tbody>
            </table>
          </section>
          <ProductSummary data={result.product_a} />
          <ProductSummary data={result.product_b} />
        </>
      ) : null}
    </div>
  );
}
