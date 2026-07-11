"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

type NutritionDatum = {
  label: string;
  value?: number | null;
  a?: number | null;
  b?: number | null;
};

export function NutritionChart({ data, mode = "single" }: { data: NutritionDatum[]; mode?: "single" | "compare" }) {
  const clean = data.map((item) => ({
    ...item,
    value: item.value ?? 0,
    a: item.a ?? 0,
    b: item.b ?? 0
  }));
  return (
    <div className="chart">
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={clean} layout={mode === "single" ? "vertical" : "horizontal"} margin={{ top: 8, right: 20, bottom: 8, left: 16 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" />
          {mode === "single" ? (
            <>
              <XAxis type="number" />
              <YAxis dataKey="label" type="category" width={110} />
              <Tooltip />
              <Bar dataKey="value" fill="var(--accent)" radius={[0, 6, 6, 0]} />
            </>
          ) : (
            <>
              <XAxis dataKey="label" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="a" name="Product A" fill="var(--accent)" radius={[6, 6, 0, 0]} />
              <Bar dataKey="b" name="Product B" fill="var(--accent-2)" radius={[6, 6, 0, 0]} />
            </>
          )}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
