"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, FlaskConical, ScanLine } from "lucide-react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { apiFetch } from "@/lib/api";
import { useAuth } from "./AuthProvider";

type Dashboard = {
  metrics: Array<{ label: string; value: number; detail: string }>;
  risk_distribution: Record<string, number>;
  top_warnings: Array<{ warning: string; count: number }>;
  recent_scans: Array<{ barcode: string; product_name?: string | null; score?: number | null; created_at: string }>;
};

const colors: Record<string, string> = { low: "#138a5b", medium: "#d28a16", high: "#c43d32" };

export function DashboardPanel() {
  const { user, enterDemo } = useAuth();
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    void apiFetch<Dashboard>("/api/dashboard").then(setData).catch((err) => setError(err instanceof Error ? err.message : "Dashboard failed"));
  }, [user]);

  if (!user) {
    return (
      <div className="workspace-welcome">
        <section>
          <p className="eyebrow">NutriLens AI workspace</p>
          <h1>Scan food. Understand the label. Build better shopping habits.</h1>
          <p className="muted">Open a demo workspace with isolated pantry, scan history, meal plans, favorites, and cited nutrition answers.</p>
          <div className="toolbar">
            <button className="button" onClick={() => void enterDemo()}><FlaskConical size={18} />Open demo workspace</button>
            <Link className="button secondary" href="/scan"><ScanLine size={18} />Scan without account</Link>
          </div>
        </section>
        <section className="workflow-strip" aria-label="Product workflow">
          <div><b>01</b><span>Capture barcode</span></div>
          <div><b>02</b><span>Score against goals</span></div>
          <div><b>03</b><span>Track and plan</span></div>
          <div><b>04</b><span>Review insights</span></div>
        </section>
      </div>
    );
  }

  if (error) return <p className="error">{error}</p>;
  if (!data) return <div className="loading-state">Calculating nutrition insights...</div>;

  const riskData = Object.entries(data.risk_distribution).map(([name, value]) => ({ name, value }));
  return (
    <div className="page dashboard-page">
      <div className="header">
        <div><p className="eyebrow">Personal nutrition intelligence</p><h1>Welcome back, {user.display_name}</h1><p className="muted">A live view of your product decisions and pantry.</p></div>
        <Link className="button" href="/scan"><ScanLine size={18} />Scan product</Link>
      </div>
      <section className="metric-grid">
        {data.metrics.map((metric) => <article className="metric" key={metric.label}><span>{metric.label}</span><strong>{metric.value}</strong><small>{metric.detail}</small></article>)}
      </section>
      <section className="dashboard-grid">
        <div className="card insight-chart">
          <div><p className="eyebrow">Risk mix</p><h2>Scanned products</h2></div>
          {riskData.some((item) => item.value > 0) ? (
            <ResponsiveContainer width="100%" height={240}>
              <PieChart><Pie data={riskData} dataKey="value" nameKey="name" innerRadius={55} outerRadius={85}>{riskData.map((item) => <Cell key={item.name} fill={colors[item.name]} />)}</Pie><Tooltip /></PieChart>
            </ResponsiveContainer>
          ) : <div className="empty-state">Scan a product to build your risk profile.</div>}
          <div className="legend">{riskData.map((item) => <span key={item.name}><i style={{ background: colors[item.name] }} />{item.name} {item.value}</span>)}</div>
        </div>
        <div className="card">
          <p className="eyebrow">Recurring signals</p><h2>Top warnings</h2>
          <ul className="rank-list">{data.top_warnings.map((item) => <li key={item.warning}><span>{item.warning}</span><b>{item.count}</b></li>)}{!data.top_warnings.length ? <li className="muted">No warning patterns yet.</li> : null}</ul>
        </div>
      </section>
      <section className="card">
        <div className="section-heading"><div><p className="eyebrow">Recent activity</p><h2>Latest scans</h2></div><Link href="/scan">View scanner <ArrowRight size={16} /></Link></div>
        <div className="activity-table">{data.recent_scans.map((scan) => <Link href={`/product/${scan.barcode}`} key={`${scan.barcode}-${scan.created_at}`}><span><b>{scan.product_name ?? scan.barcode}</b><small>{new Date(scan.created_at).toLocaleString()}</small></span><strong className={`score-text score-${scan.score && scan.score >= 75 ? "good" : scan.score && scan.score < 45 ? "bad" : "medium"}`}>{scan.score ?? "-"}</strong></Link>)}{!data.recent_scans.length ? <div className="empty-state">Your recent scans will appear here.</div> : null}</div>
      </section>
    </div>
  );
}
