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
    <div className="page">
      <div>
        <p className="eyebrow">Meal planner</p>
        <h1>Rule-based shopping plan</h1>
      </div>
      <section className="card toolbar">
        <label className="field"><span>Days</span><input type="number" min={1} max={14} value={days} onChange={(event) => setDays(Number(event.target.value))} /></label>
        <label className="field"><span>Budget</span><input type="number" value={budget} onChange={(event) => setBudget(Number(event.target.value))} /></label>
        <label className="field"><span>Goal</span><select value={goal} onChange={(event) => setGoal(event.target.value)}><option value="low_sugar">Low sugar</option><option value="high_protein">High protein</option><option value="weight_loss">Weight loss</option><option value="vegan">Vegan</option><option value="general">General</option></select></label>
        <button className="button secondary" onClick={importPantry}><PackageSearch size={18} />Import pantry</button>
        <button className="button" onClick={generate}><Soup size={18} />Generate</button>
      </section>
      {availableItems.length ? <section className="card"><h2>Available items</h2><div className="toolbar">{availableItems.map((item) => <span className="badge" key={item}>{item}</span>)}</div></section> : null}
      {plan ? (
        <section className="grid two">
          <div className="card"><h2>Meals</h2><ul className="list">{plan.meals.map((meal) => <li key={String(meal.day)}><strong>Day {meal.day}</strong><br />{meal.breakfast}<br />{meal.lunch}<br />{meal.dinner}</li>)}</ul></div>
          <div className="card"><h2>Shopping list</h2><ul className="list">{plan.shopping_list.map((item) => <li key={item.item}>{item.item}: {item.quantity}</li>)}</ul><h3>Warnings</h3><ul className="list">{plan.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></div>
        </section>
      ) : null}
    </div>
  );
}
