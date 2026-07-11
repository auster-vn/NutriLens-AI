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
    <div className="page">
      <div>
        <p className="eyebrow">User profile</p>
        <h1>Personalize warnings</h1>
        <p className="muted">The demo stores only practical preference fields, not disease descriptions.</p>
      </div>
      <section className="card grid two">
        <label className="field"><span>Goal</span><select value={profile.goal} onChange={(event) => setProfile({ ...profile, goal: event.target.value })}>{goals.map((goal) => <option key={goal} value={goal}>{goal}</option>)}</select></label>
        <label className="field"><span>Diet</span><input value={profile.diet ?? ""} onChange={(event) => setProfile({ ...profile, diet: event.target.value })} /></label>
        <label className="field"><span>Allergies, comma separated</span><input value={profile.allergies.join(", ")} onChange={(event) => setProfile({ ...profile, allergies: event.target.value.split(",").map((item) => item.trim()).filter(Boolean) })} /></label>
        <label className="field"><span>Disliked ingredients</span><input value={profile.disliked_ingredients.join(", ")} onChange={(event) => setProfile({ ...profile, disliked_ingredients: event.target.value.split(",").map((item) => item.trim()).filter(Boolean) })} /></label>
        <label className="field"><span>Daily budget</span><input type="number" value={profile.budget_daily ?? ""} onChange={(event) => setProfile({ ...profile, budget_daily: Number(event.target.value) || null })} /></label>
        <div className="toolbar" style={{ alignItems: "end" }}><button className="button" onClick={save}><Save size={18} />Save</button>{message ? <span className="badge">{message}</span> : null}</div>
      </section>
    </div>
  );
}
