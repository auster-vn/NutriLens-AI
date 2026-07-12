"use client";

import { useState } from "react";
import { AlertTriangle, PackageSearch, Soup, Target, WalletCards } from "lucide-react";
import { apiFetch, toUserMessage, type TdeeResult, type UserProfile } from "@/lib/api";

type PlannedMeal = { type: string; label: string; name: string; calories_kcal: number; protein_g: number; fiber_g: number; estimated_cost_vnd: number; reason: string; pantry_matches: string[] };
type PlannedDay = { day: number; meals: PlannedMeal[] };
type MealPlan = {
  days: number; budget?: number | null; goal: string; diet: string; meals_per_day: number; target_calories?: number | null;
  meals: PlannedDay[]; shopping_list: Array<{ item: string; quantity: string }>;
  estimated_nutrition: Record<string, number>; warnings: string[];
};

const money = new Intl.NumberFormat("vi-VN");

export function MealPlannerPanel() {
  const [days, setDays] = useState(3);
  const [budget, setBudget] = useState(450000);
  const [goal, setGoal] = useState("general");
  const [diet, setDiet] = useState("general");
  const [targetCalories, setTargetCalories] = useState(1800);
  const [excluded, setExcluded] = useState("");
  const [availableItems, setAvailableItems] = useState<string[]>([]);
  const [plan, setPlan] = useState<MealPlan | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function generate() {
    setLoading(true); setError(null);
    try {
      setPlan(await apiFetch<MealPlan>("/api/meal-plan/generate", { method: "POST", body: JSON.stringify({ days, budget: budget || null, goal, diet, meals_per_day: 3, target_calories: targetCalories || null, excluded_ingredients: excluded.split(",").map((item) => item.trim()).filter(Boolean), available_items: availableItems }) }));
    } catch (err) { setError(toUserMessage(err, "Không thể tạo kế hoạch bữa ăn.")); }
    finally { setLoading(false); }
  }

  async function importPantry() {
    try {
      const rows = await apiFetch<Array<{ product_name?: string | null; barcode: string }>>("/api/pantry");
      setAvailableItems(rows.map((item) => item.product_name ?? item.barcode).slice(0, 12));
    } catch (err) { setError(toUserMessage(err, "Không thể đọc dữ liệu tủ đồ.")); }
  }

  async function importTdeeTarget() {
    setError(null);
    try {
      const profile = await apiFetch<UserProfile>("/api/profile");
      const recommendation = await apiFetch<TdeeResult>("/api/profile/tdee", {
        method: "POST",
        body: JSON.stringify(profile),
      });
      setTargetCalories(recommendation.target_calories_kcal);
      if (profile.goal) setGoal(profile.goal);
      if (profile.diet) setDiet(profile.diet);
      if (profile.budget_daily) setBudget(profile.budget_daily * days);
    } catch (err) { setError(toUserMessage(err, "Không thể tính TDEE từ hồ sơ.")); }
  }

  return <div className="page animate-slide-up">
    <div className="header"><div><p className="eyebrow">Lập kế hoạch bữa ăn</p><h1>Thực đơn theo mục tiêu</h1><p className="muted">Tạo thực đơn đa dạng, lọc dị ứng và gom nguyên liệu thành danh sách mua sắm thực tế.</p></div></div>
    <section className="card grid">
      <div className="meal-settings">
        <label className="field"><span>Số ngày</span><input type="number" min={1} max={14} value={days} onChange={(e) => setDays(Number(e.target.value))} /></label>
        <label className="field"><span>Ngân sách tổng (VND)</span><input type="number" min={0} value={budget} onChange={(e) => setBudget(Number(e.target.value))} /></label>
        <label className="field"><span>Kcal mục tiêu/ngày</span><input type="number" min={800} max={5000} value={targetCalories} onChange={(e) => setTargetCalories(Number(e.target.value))} /></label>
        <label className="field"><span>Mục tiêu</span><select value={goal} onChange={(e) => setGoal(e.target.value)}><option value="general">Cân bằng</option><option value="low_sugar">Ít đường</option><option value="high_protein">Nhiều protein</option><option value="weight_loss">Kiểm soát cân nặng</option><option value="vegan">Thực vật</option></select></label>
        <label className="field"><span>Chế độ ăn</span><select value={diet} onChange={(e) => setDiet(e.target.value)}><option value="general">Không giới hạn</option><option value="vegetarian">Ăn chay có trứng/sữa</option><option value="vegan">Thuần thực vật</option><option value="pescatarian">Có cá, không thịt</option></select></label>
      </div>
      <label className="field"><span>Nguyên liệu cần tránh (phân cách bằng dấu phẩy)</span><input value={excluded} onChange={(e) => setExcluded(e.target.value)} placeholder="ví dụ: đậu phộng, sữa, tôm" /></label>
      <div className="toolbar"><button className="button secondary" onClick={() => void importTdeeTarget()}><Target size={16} />Dùng target từ TDEE</button><button className="button secondary" onClick={() => void importPantry()}><PackageSearch size={16} />Dùng nguyên liệu trong tủ</button><button className="button" onClick={() => void generate()} disabled={loading}><Soup size={16} />{loading ? "Đang tối ưu…" : "Tạo thực đơn"}</button></div>
      {availableItems.length ? <div className="toolbar">{availableItems.map((item) => <span className="badge" key={item}>{item}</span>)}</div> : null}
      {error ? <p className="error">{error}</p> : null}
    </section>

    {plan ? <>
      <section className="metric-grid">
        <article className="metric"><Target size={17} /><span>Kcal trung bình</span><strong>{plan.estimated_nutrition.daily_calories_kcal}</strong><small>kcal/ngày</small></article>
        <article className="metric"><span>Protein</span><strong>{plan.estimated_nutrition.daily_protein_g}g</strong><small>trung bình/ngày</small></article>
        <article className="metric"><span>Chất xơ</span><strong>{plan.estimated_nutrition.daily_fiber_g}g</strong><small>trung bình/ngày</small></article>
        <article className="metric"><WalletCards size={17} /><span>Chi phí dự kiến</span><strong>{money.format(plan.estimated_nutrition.estimated_cost_vnd)}đ</strong><small>toàn kế hoạch</small></article>
      </section>
      <section className="meal-plan-layout">
        <div className="meal-days">{plan.meals.map((day) => <article className="card meal-day" key={day.day}><div className="meal-day-heading"><span>Ngày {day.day}</span><small>{day.meals.reduce((sum, meal) => sum + meal.calories_kcal, 0)} kcal</small></div><div className="meal-slot-list">{day.meals.map((meal) => <div className="meal-slot" key={meal.type}><div><span className="eyebrow">{meal.label}</span><h3>{meal.name}</h3><p>{meal.reason}</p></div><div className="meal-macros"><span>{meal.calories_kcal} kcal</span><span>{meal.protein_g}g protein</span><span>{money.format(meal.estimated_cost_vnd)}đ</span></div></div>)}</div></article>)}</div>
        <aside className="card shopping-panel"><h2>Danh sách mua sắm</h2><p className="muted">Đã loại các nguyên liệu khớp với pantry.</p><ul className="list">{plan.shopping_list.map((item) => <li key={`${item.item}-${item.quantity}`}><span>{item.item}</span><strong>{item.quantity}</strong></li>)}</ul></aside>
      </section>
      {plan.warnings.length ? <section className="notice warning"><AlertTriangle size={18} /><div><strong>Lưu ý khi áp dụng</strong>{plan.warnings.map((warning) => <p key={warning}>{warning}</p>)}</div></section> : null}
    </> : null}
  </div>;
}
