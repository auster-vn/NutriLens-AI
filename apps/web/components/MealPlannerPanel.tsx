"use client";

import { useState } from "react";
import { PackageSearch, Soup } from "lucide-react";
import { apiFetch } from "@/lib/api";

type MealPlan = {
  days: number;
  budget?: number | null;
  goal: string;
  meals: Array<Record<string, string | number>>;
  shopping_list: Array<Record<string, string>>;
  estimated_nutrition: Record<string, string>;
  warnings: string[];
};

export function MealPlannerPanel() {
  const [days, setDays] = useState(3);
  const [budget, setBudget] = useState(300000);
  const [goal, setGoal] = useState("low_sugar");
  const [availableItems, setAvailableItems] = useState<string[]>([]);
  const [plan, setPlan] = useState<MealPlan | null>(null);

  async function generate() {
    setPlan(await apiFetch<MealPlan>("/api/meal-plan/generate", {
      method: "POST",
      body: JSON.stringify({ days, budget, goal, excluded_ingredients: [], available_items: availableItems })
    }));
  }

  async function importPantry() {
    const rows = await apiFetch<Array<{ product_name?: string | null; barcode: string }>>("/api/pantry");
    setAvailableItems(rows.map((item) => item.product_name ?? item.barcode).slice(0, 8));
  }

  return (
    <div className="page animate-slide-up">
      <div className="header">
        <div>
          <p className="eyebrow">Lập kế hoạch bữa ăn</p>
          <h1>Kế hoạch mua sắm</h1>
          <p className="muted">Tự động tạo kế hoạch bữa ăn và danh sách mua sắm theo mục tiêu dinh dưỡng.</p>
        </div>
      </div>

      <section className="card">
        <h2 style={{ marginBottom: 14 }}>Thiết lập</h2>
        <div className="toolbar" style={{ gap: 12, alignItems: "flex-end" }}>
          <label className="field" style={{ flex: "0 1 80px" }}>
            <span>Số ngày</span>
            <input type="number" min={1} max={14} value={days} onChange={(e) => setDays(Number(e.target.value))} />
          </label>
          <label className="field" style={{ flex: "1 1 120px" }}>
            <span>Ngân sách (VND)</span>
            <input type="number" value={budget} onChange={(e) => setBudget(Number(e.target.value))} />
          </label>
          <label className="field" style={{ flex: "1 1 150px" }}>
            <span>Mục tiêu</span>
            <select value={goal} onChange={(e) => setGoal(e.target.value)}>
              <option value="low_sugar">Ít đường</option>
              <option value="high_protein">Nhiều protein</option>
              <option value="weight_loss">Giảm cân</option>
              <option value="vegan">Thực vật</option>
              <option value="general">Tổng quát</option>
            </select>
          </label>
          <button className="button secondary" onClick={importPantry}>
            <PackageSearch size={16} />
            Nhập từ tủ đồ
          </button>
          <button className="button" onClick={generate}>
            <Soup size={16} />
            Tạo kế hoạch
          </button>
        </div>
      </section>

      {availableItems.length ? (
        <section className="card">
          <h2 style={{ marginBottom: 10 }}>Vật phẩm sẵn có</h2>
          <div className="toolbar">
            {availableItems.map((item) => (
              <span className="badge" key={item}>{item}</span>
            ))}
          </div>
        </section>
      ) : null}

      {plan ? (
        <section className="grid two">
          <div className="card">
            <h2>Bữa ăn</h2>
            <ul className="list">
              {plan.meals.map((meal) => (
                <li key={String(meal.day)}>
                  <strong style={{ color: "var(--green)" }}>Ngày {meal.day}</strong>
                  <div style={{ marginTop: 4, fontSize: 13, color: "var(--ink-2)", display: "grid", gap: 2 }}>
                    <span>Sáng: {String(meal.breakfast)}</span>
                    <span>Trưa: {String(meal.lunch)}</span>
                    <span>Tối: {String(meal.dinner)}</span>
                  </div>
                </li>
              ))}
            </ul>
          </div>
          <div className="card">
            <h2>Danh sách mua sắm</h2>
            <ul className="list">
              {plan.shopping_list.map((item) => (
                <li key={item.item} style={{ display: "flex", justifyContent: "space-between" }}>
                  <span>{item.item}</span>
                  <span className="muted">{item.quantity}</span>
                </li>
              ))}
            </ul>
            {plan.warnings.length ? (
              <>
                <h3 style={{ marginTop: 16, color: "var(--warn)" }}>Cảnh báo</h3>
                <ul className="list">
                  {plan.warnings.map((warning) => (
                    <li key={warning} style={{ color: "var(--warn)" }}>{warning}</li>
                  ))}
                </ul>
              </>
            ) : null}
          </div>
        </section>
      ) : null}
    </div>
  );
}
