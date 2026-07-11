"use client";

import { useEffect, useState } from "react";
import { Activity, Calculator, Save } from "lucide-react";
import { apiFetch, defaultProfile, type TdeeResult, type UserProfile } from "@/lib/api";

const goals = ["general", "low_sugar", "low_sodium", "high_protein", "weight_loss", "vegetarian", "vegan", "gluten_free", "lactose_free"];
const activityOptions = [
  ["sedentary", "Ít vận động - công việc ngồi nhiều"],
  ["light", "Nhẹ - tập 1-3 buổi/tuần"],
  ["moderate", "Vừa - tập 3-5 buổi/tuần"],
  ["very_active", "Cao - tập 6-7 buổi/tuần"],
  ["extra_active", "Rất cao - lao động nặng hoặc tập 2 lần/ngày"],
] as const;

export function ProfilePanel() {
  const [profile, setProfile] = useState<UserProfile>(defaultProfile);
  const [result, setResult] = useState<TdeeResult | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { void apiFetch<UserProfile>("/api/profile").then(setProfile).catch(() => undefined); }, []);

  async function save() {
    setError(null);
    try {
      const saved = await apiFetch<UserProfile>("/api/profile", { method: "PUT", body: JSON.stringify(profile) });
      setProfile(saved); setMessage("Đã lưu hồ sơ");
    } catch (err) { setError(err instanceof Error ? err.message : "Không thể lưu hồ sơ"); }
  }

  async function calculate() {
    setError(null);
    try { setResult(await apiFetch<TdeeResult>("/api/profile/tdee", { method: "POST", body: JSON.stringify(profile) })); }
    catch (err) { setError(err instanceof Error ? err.message : "Không thể tính TDEE"); }
  }

  const numeric = (field: keyof UserProfile, value: string) => setProfile({ ...profile, [field]: value === "" ? null : Number(value) });

  return <div className="page animate-slide-up">
    <div className="header"><div><p className="eyebrow">Hồ sơ cá nhân</p><h1>Nhu cầu năng lượng</h1><p className="muted">Tính TDEE và calorie target từ dữ liệu cơ thể, vận động và tốc độ giảm cân mong muốn.</p></div></div>

    <section className="card grid">
      <div><p className="eyebrow">Dữ liệu bắt buộc</p><h2>Thông tin tính TDEE</h2></div>
      <div className="profile-metrics-grid">
        <label className="field"><span>Giới tính sinh học</span><select value={profile.biological_sex ?? ""} onChange={(e) => setProfile({ ...profile, biological_sex: (e.target.value || null) as UserProfile["biological_sex"] })}><option value="">Chọn</option><option value="male">Nam</option><option value="female">Nữ</option></select></label>
        <label className="field"><span>Tuổi</span><input type="number" min={18} max={100} value={profile.age ?? ""} onChange={(e) => numeric("age", e.target.value)} /></label>
        <label className="field"><span>Chiều cao (cm)</span><input type="number" min={120} max={230} value={profile.height_cm ?? ""} onChange={(e) => numeric("height_cm", e.target.value)} /></label>
        <label className="field"><span>Cân nặng (kg)</span><input type="number" min={30} max={350} step="0.1" value={profile.weight_kg ?? ""} onChange={(e) => numeric("weight_kg", e.target.value)} /></label>
        <label className="field"><span>Mức vận động</span><select value={profile.activity_level ?? ""} onChange={(e) => setProfile({ ...profile, activity_level: (e.target.value || null) as UserProfile["activity_level"] })}><option value="">Chọn mức vận động</option>{activityOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
        <label className="field"><span>Mục tiêu giảm (kg/tuần)</span><input type="number" min={0} max={1.5} step="0.1" value={profile.target_weight_loss_kg_week ?? ""} onChange={(e) => numeric("target_weight_loss_kg_week", e.target.value)} /><small className="muted">0 để duy trì; hệ thống sẽ giới hạn mục tiêu quá cao.</small></label>
      </div>
      <div className="toolbar"><button className="button" onClick={() => void calculate()}><Calculator size={16} />Tính TDEE và thâm hụt</button><button className="button secondary" onClick={() => void save()}><Save size={16} />Lưu vào hồ sơ</button>{message ? <span className="badge">{message}</span> : null}</div>
      {error ? <p className="error">{error}</p> : null}
    </section>

    {result ? <section className="grid">
      <div className="metric-grid">
        <article className="metric"><Activity size={17} /><span>BMR</span><strong>{result.bmr_kcal}</strong><small>kcal/ngày khi nghỉ</small></article>
        <article className="metric"><span>TDEE</span><strong>{result.tdee_kcal}</strong><small>kcal duy trì ước tính</small></article>
        <article className="metric"><span>Thâm hụt đề xuất</span><strong>{result.recommended_deficit_kcal}</strong><small>kcal/ngày</small></article>
        <article className="metric"><span>Calorie target</span><strong>{result.target_calories_kcal}</strong><small>kcal/ngày</small></article>
      </div>
      <section className="card tdee-summary"><div><span className="muted">Khoảng duy trì</span><strong>{result.maintenance_range_kcal[0]}-{result.maintenance_range_kcal[1]} kcal</strong></div><div><span className="muted">Tốc độ giảm được đề xuất</span><strong>{result.recommended_loss_kg_week} kg/tuần</strong></div><div><span className="muted">Thâm hụt bạn yêu cầu</span><strong>{result.requested_deficit_kcal} kcal/ngày</strong></div></section>
      <section className="notice warning"><div>{result.warnings.map((warning) => <p key={warning}>{warning}</p>)}</div></section>
    </section> : null}

    <section className="card grid"><div><p className="eyebrow">Cá nhân hóa thực phẩm</p><h2>Sở thích và giới hạn</h2></div><div className="grid two">
      <label className="field"><span>Mục tiêu dinh dưỡng</span><select value={profile.goal} onChange={(e) => setProfile({ ...profile, goal: e.target.value })}>{goals.map((goal) => <option key={goal} value={goal}>{goal}</option>)}</select></label>
      <label className="field"><span>Chế độ ăn</span><input value={profile.diet ?? ""} onChange={(e) => setProfile({ ...profile, diet: e.target.value })} placeholder="vegetarian, vegan..." /></label>
      <label className="field"><span>Dị ứng</span><input value={profile.allergies.join(", ")} onChange={(e) => setProfile({ ...profile, allergies: e.target.value.split(",").map((item) => item.trim()).filter(Boolean) })} /></label>
      <label className="field"><span>Nguyên liệu không thích</span><input value={profile.disliked_ingredients.join(", ")} onChange={(e) => setProfile({ ...profile, disliked_ingredients: e.target.value.split(",").map((item) => item.trim()).filter(Boolean) })} /></label>
      <label className="field"><span>Ngân sách ngày (VND)</span><input type="number" value={profile.budget_daily ?? ""} onChange={(e) => numeric("budget_daily", e.target.value)} /></label>
    </div></section>
  </div>;
}
