import Image from "next/image";
import type { ProductWithScore } from "@/lib/api";
import { NutritionChart } from "./NutritionChart";

const nutritionKeys = [
  ["energy-kcal_100g", "Calories"],
  ["sugars_100g", "Đường"],
  ["sodium_100g", "Sodium"],
  ["salt_100g", "Muối"],
  ["saturated-fat_100g", "Béo bão hòa"],
  ["proteins_100g", "Protein"],
  ["fiber_100g", "Chất xơ"]
];

export function ProductSummary({ data }: { data: ProductWithScore }) {
  const { product, score } = data;
  const chartData = nutritionKeys.map(([key, label]) => ({
    label,
    value: typeof product.nutriments[key] === "number" ? product.nutriments[key] as number : Number(product.nutriments[key] ?? 0)
  }));
  return (
    <div className="grid two">
      <section className="card">
        <div className="toolbar" style={{ alignItems: "flex-start" }}>
          {product.image_url ? (
            <Image src={product.image_url} alt={product.name ?? product.barcode} width={120} height={120} style={{ objectFit: "contain" }} />
          ) : null}
          <div>
            <span className="badge">{product.source}</span>
            <h2 style={{ marginTop: 12 }}>{product.name ?? "Unnamed product"}</h2>
            <p className="muted">{product.brand ?? "Unknown brand"} · {product.barcode}</p>
            {product.nutriscore ? <p>Nutri-Score: <strong>{product.nutriscore.toUpperCase()}</strong></p> : null}
          </div>
        </div>
        <h3>Ingredients</h3>
        <p className="muted">{product.ingredients_text || "No ingredient text available."}</p>
      </section>
      <section className="card">
        <div className="toolbar">
          <div className="score">{score.score}</div>
          <div>
            <h2>{score.label}</h2>
            <p className="muted">Risk level: {score.risk_level}</p>
          </div>
        </div>
        <h3>Warnings</h3>
        <ul className="list">{score.warnings.map((item) => <li key={item}>{item}</li>)}</ul>
        {score.good_points.length ? (
          <>
            <h3 style={{ marginTop: 16 }}>Good points</h3>
            <ul className="list">{score.good_points.map((item) => <li key={item}>{item}</li>)}</ul>
          </>
        ) : null}
      </section>
      <section className="card">
        <h2>Nutrition per 100g/ml</h2>
        <NutritionChart data={chartData} />
        <table className="table">
          <tbody>
            {nutritionKeys.map(([key, label]) => (
              <tr key={key}>
                <th>{label}</th>
                <td>{String(product.nutriments[key] ?? "Missing")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <section className="card">
        <h2>Safety data</h2>
        <p><strong>Allergens:</strong> {product.allergens.length ? product.allergens.join(", ") : "Missing"}</p>
        <p><strong>Additives:</strong> {product.additives.length ? product.additives.join(", ") : "None listed"}</p>
        <p><strong>Missing data:</strong> {score.missing_data.length ? score.missing_data.join(", ") : "None flagged"}</p>
        <p><strong>Completeness:</strong> {product.completeness_score ?? "n/a"}%</p>
        <p className="muted">{score.disclaimer}</p>
      </section>
    </div>
  );
}
