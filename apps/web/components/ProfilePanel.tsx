"use client";

import { useEffect, useState } from "react";
import { Save } from "lucide-react";
import { apiFetch, defaultProfile, type UserProfile } from "@/lib/api";

const goals = ["general", "low_sugar", "low_sodium", "high_protein", "weight_loss", "vegetarian", "vegan", "gluten_free", "lactose_free"];

export function ProfilePanel() {
  const [profile, setProfile] = useState<UserProfile>(defaultProfile);
  const [message, setMessage] = useState("");

  useEffect(() => {
    void apiFetch<UserProfile>("/api/profile").then(setProfile).catch(() => undefined);
  }, []);

  async function save() {
    const saved = await apiFetch<UserProfile>("/api/profile", { method: "PUT", body: JSON.stringify(profile) });
    setProfile(saved);
    setMessage("Saved");
  }

  return (
    <div className="page animate-slide-up">
      <div className="header">
        <div>
          <p className="eyebrow">Hồ sơ người dùng</p>
          <h1>Tùy chỉnh cảnh báo</h1>
          <p className="muted">Chỉ lưu các trường sở thích thực tế, không lưu mô tả bệnh lý.</p>
        </div>
      </div>

      <section className="card grid two">
        <label className="field">
          <span>Mục tiêu dinh dưỡng</span>
          <select
            value={profile.goal}
            onChange={(e) => setProfile({ ...profile, goal: e.target.value })}
          >
            {goals.map((g) => <option key={g} value={g}>{g}</option>)}
          </select>
        </label>

        <label className="field">
          <span>Chế độ ăn</span>
          <input
            value={profile.diet ?? ""}
            onChange={(e) => setProfile({ ...profile, diet: e.target.value })}
            placeholder="e.g. vegetarian, keto..."
          />
        </label>

        <label className="field">
          <span>Dị ứng (cách nhau bằng dấu phẩy)</span>
          <input
            value={profile.allergies.join(", ")}
            onChange={(e) =>
              setProfile({
                ...profile,
                allergies: e.target.value
                  .split(",")
                  .map((item) => item.trim())
                  .filter(Boolean),
              })
            }
            placeholder="e.g. gluten, dairy, nuts"
          />
        </label>

        <label className="field">
          <span>Nguyên liệu không thích</span>
          <input
            value={profile.disliked_ingredients.join(", ")}
            onChange={(e) =>
              setProfile({
                ...profile,
                disliked_ingredients: e.target.value
                  .split(",")
                  .map((item) => item.trim())
                  .filter(Boolean),
              })
            }
            placeholder="e.g. msg, palm oil..."
          />
        </label>

        <label className="field">
          <span>Ngân sách ngày (VND)</span>
          <input
            type="number"
            value={profile.budget_daily ?? ""}
            onChange={(e) =>
              setProfile({ ...profile, budget_daily: Number(e.target.value) || null })
            }
            placeholder="e.g. 150000"
          />
        </label>

        <div className="toolbar" style={{ alignItems: "flex-end" }}>
          <button className="button" onClick={save}>
            <Save size={16} />
            Lưu thay đổi
          </button>
          {message ? <span className="badge" style={{ background: "var(--good-bg)", color: "var(--good)" }}>{message}</span> : null}
        </div>
      </section>
    </div>
  );
}
