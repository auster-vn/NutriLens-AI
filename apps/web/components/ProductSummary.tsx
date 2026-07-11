import Image from "next/image";
import type { ProductWithScore } from "@/lib/api";
import { NutritionChart } from "./NutritionChart";
import { AlertTriangle, CheckCircle, ShieldAlert, Info } from "lucide-react";

const nutritionKeys: [string, string, string][] = [
  ["energy-kcal_100g",    "Calo",         "kcal"],
  ["sugars_100g",         "Đường",         "g"],
  ["sodium_100g",         "Natri",         "mg"],
  ["salt_100g",           "Muối",          "g"],
  ["saturated-fat_100g",  "Béo bão hòa",   "g"],
  ["proteins_100g",       "Protein",       "g"],
  ["fiber_100g",          "Chất xơ",       "g"],
];

const riskColors: Record<string, string> = {
  low:    "var(--good)",
  medium: "var(--warn)",
  high:   "var(--danger)",
};

const riskBgColors: Record<string, string> = {
  low:    "var(--good-bg)",
  medium: "var(--warn-bg)",
  high:   "var(--danger-bg)",
};

const riskLabel: Record<string, string> = {
  low:    "Thấp",
  medium: "Trung bình",
  high:   "Cao",
};

function scoreClass(score: number) {
  if (score >= 75) return "score-good";
  if (score < 45) return "score-bad";
  return "score-medium";
}

export function ProductSummary({ data }: { data: ProductWithScore }) {
  const { product, score } = data;
  const chartData = nutritionKeys.map(([key, label]) => ({
    label,
    value:
      typeof product.nutriments[key] === "number"
        ? (product.nutriments[key] as number)
        : Number(product.nutriments[key] ?? 0),
  }));

  const riskColor = riskColors[score.risk_level] ?? "var(--muted)";
  const riskBg    = riskBgColors[score.risk_level] ?? "var(--bg-2)";

  return (
    <div className="grid two" style={{ gap: 16 }}>
      {/* Product info card */}
      <section className="card">
        <div style={{ display: "flex", gap: 16, alignItems: "flex-start", marginBottom: 16 }}>
          {product.image_url ? (
            <div style={{
              width: 100, height: 100, borderRadius: "var(--r)", overflow: "hidden",
              border: "1px solid var(--line)", background: "var(--bg-2)",
              display: "grid", placeItems: "center", flexShrink: 0,
            }}>
              <Image
                src={product.image_url}
                alt={product.name ?? product.barcode}
                width={96}
                height={96}
                style={{ objectFit: "contain", maxWidth: "100%", maxHeight: "100%" }}
              />
            </div>
          ) : null}
          <div style={{ flex: 1, minWidth: 0 }}>
            <span className="badge" style={{ marginBottom: 8 }}>{product.source}</span>
            <h2 style={{ marginTop: 6, marginBottom: 4, fontSize: 16 }}>
              {product.name ?? "Sản phẩm chưa đặt tên"}
            </h2>
            <p className="muted" style={{ margin: 0, fontSize: 13 }}>
              {product.brand ?? "Thương hiệu chưa xác định"} · {product.barcode}
            </p>
            {product.nutriscore ? (
              <div style={{ marginTop: 10 }}>
                <span style={{
                  display: "inline-flex", alignItems: "center",
                  padding: "3px 10px", borderRadius: "var(--r-sm)",
                  background: "var(--green-light)", color: "var(--green)",
                  fontSize: 12, fontWeight: 700,
                }}>
                  Nutri-Score: {product.nutriscore.toUpperCase()}
                </span>
              </div>
            ) : null}
          </div>
        </div>

        <div style={{ borderTop: "1px solid var(--line)", paddingTop: 14 }}>
          <h3 style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
            <Info size={13} style={{ color: "var(--muted)" }} />
            Thành phần
          </h3>
          <p className="muted" style={{ fontSize: 13, lineHeight: 1.7, margin: 0 }}>
            {product.ingredients_text || "Không có thông tin thành phần."}
          </p>
        </div>
      </section>

      {/* Score card */}
      <section className="card">
        <div style={{ display: "flex", gap: 16, alignItems: "center", marginBottom: 18 }}>
          <div className={`score ${scoreClass(score.score)}`}>{score.score}</div>
          <div>
            <h2 style={{ marginBottom: 4, fontSize: 17 }}>{score.label}</h2>
            <span style={{
              display: "inline-flex", alignItems: "center", gap: 5,
              padding: "3px 10px", borderRadius: "var(--r-sm)",
              background: riskBg, color: riskColor,
              fontSize: 12, fontWeight: 700,
            }}>
              Rủi ro: {riskLabel[score.risk_level] ?? score.risk_level}
            </span>
          </div>
        </div>

        {score.warnings.length ? (
          <>
            <h3 style={{ display: "flex", alignItems: "center", gap: 6, color: "var(--danger)" }}>
              <AlertTriangle size={13} />
              Cảnh báo
            </h3>
            <ul className="list" style={{ marginBottom: 16 }}>
              {score.warnings.map((item) => (
                <li key={item} style={{ color: "var(--ink-2)" }}>{item}</li>
              ))}
            </ul>
          </>
        ) : null}

        {score.good_points.length ? (
          <>
            <h3 style={{ display: "flex", alignItems: "center", gap: 6, color: "var(--good)" }}>
              <CheckCircle size={13} />
              Điểm tích cực
            </h3>
            <ul className="list">
              {score.good_points.map((item) => (
                <li key={item} style={{ color: "var(--ink-2)" }}>{item}</li>
              ))}
            </ul>
          </>
        ) : null}
      </section>

      {/* Nutrition chart */}
      <section className="card">
        <h2 style={{ marginBottom: 16 }}>Dinh dưỡng / 100g</h2>
        <NutritionChart data={chartData} />
        <table className="table" style={{ marginTop: 14 }}>
          <thead>
            <tr>
              <th>Chất dinh dưỡng</th>
              <th>Giá trị</th>
              <th>Đơn vị</th>
            </tr>
          </thead>
          <tbody>
            {nutritionKeys.map(([key, label, unit]) => (
              <tr key={key}>
                <td style={{ fontWeight: 500 }}>{label}</td>
                <td style={{ fontWeight: 700 }}>
                  {product.nutriments[key] != null
                    ? String(product.nutriments[key])
                    : <span className="muted">–</span>}
                </td>
                <td className="muted">{unit}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {/* Safety card */}
      <section className="card">
        <h2 style={{ marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
          <ShieldAlert size={18} style={{ color: "var(--warn)" }} />
          Thông tin an toàn
        </h2>
        <div style={{ display: "grid", gap: 14 }}>
          <div>
            <p style={{ margin: "0 0 4px", fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.07em", color: "var(--muted)" }}>
              Chất gây dị ứng
            </p>
            <p style={{ margin: 0, fontSize: 13.5, color: "var(--ink-2)" }}>
              {product.allergens.length ? product.allergens.join(", ") : "Không có thông tin"}
            </p>
          </div>
          <div>
            <p style={{ margin: "0 0 4px", fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.07em", color: "var(--muted)" }}>
              Chất phụ gia
            </p>
            <p style={{ margin: 0, fontSize: 13.5, color: "var(--ink-2)" }}>
              {product.additives.length ? product.additives.join(", ") : "Không có"}
            </p>
          </div>
          <div>
            <p style={{ margin: "0 0 4px", fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.07em", color: "var(--muted)" }}>
              Dữ liệu còn thiếu
            </p>
            <p style={{ margin: 0, fontSize: 13.5, color: "var(--ink-2)" }}>
              {score.missing_data.length ? score.missing_data.join(", ") : "Không có"}
            </p>
          </div>
          <div>
            <p style={{ margin: "0 0 4px", fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.07em", color: "var(--muted)" }}>
              Độ đầy đủ dữ liệu
            </p>
            <p style={{ margin: 0, fontSize: 13.5, fontWeight: 700, color: "var(--ink)" }}>
              {product.completeness_score != null ? `${product.completeness_score}%` : "n/a"}
            </p>
          </div>
        </div>
        {score.disclaimer ? (
          <p className="muted" style={{ marginTop: 14, marginBottom: 0, fontSize: 12, fontStyle: "italic", borderTop: "1px solid var(--line)", paddingTop: 12 }}>
            {score.disclaimer}
          </p>
        ) : null}
      </section>
    </div>
  );
}
