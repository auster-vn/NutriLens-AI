"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, FlaskConical, ScanLine, TrendingUp, Shield, Zap } from "lucide-react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { apiFetch } from "@/lib/api";
import { useAuth } from "./AuthProvider";

type Dashboard = {
  metrics: Array<{ label: string; value: number; detail: string }>;
  risk_distribution: Record<string, number>;
  top_warnings: Array<{ warning: string; count: number }>;
  recent_scans: Array<{
    barcode: string;
    product_name?: string | null;
    score?: number | null;
    created_at: string;
  }>;
};

const colors: Record<string, string> = {
  low:    "#10b981",
  medium: "#f59e0b",
  high:   "#ef4444",
};

const riskLabels: Record<string, string> = {
  low: "An toàn", medium: "Trung bình", high: "Rủi ro"
};

function ScoreClass(score: number | null | undefined) {
  if (score == null) return "medium";
  if (score >= 75) return "good";
  if (score < 45) return "bad";
  return "medium";
}

export function DashboardPanel() {
  const { user, enterDemo } = useAuth();
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    void apiFetch<Dashboard>("/api/dashboard")
      .then(setData)
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Dashboard failed")
      );
  }, [user]);

  /* ── Welcome / Hero ── */
  if (!user) {
    return (
      <div className="workspace-welcome animate-fade-in">
        <section>
          <p className="eyebrow">NutriLens AI Workspace</p>
          <h1>Quét thực phẩm. Hiểu nhãn dinh dưỡng. Xây dựng thói quen tốt hơn.</h1>
          <p className="muted" style={{ marginTop: 14, marginBottom: 28 }}>
            Mở không gian làm việc demo với lịch sử quét, kế hoạch bữa ăn, yêu thích và trợ lý dinh dưỡng AI.
          </p>
          <div className="toolbar">
            <button className="button" onClick={() => void enterDemo()}>
              <FlaskConical size={16} />
              Mở demo workspace
            </button>
            <Link className="button secondary" href="/scan">
              <ScanLine size={16} />
              Quét không cần tài khoản
            </Link>
          </div>
        </section>

        <section className="workflow-strip" aria-label="Quy trình">
          <div>
            <b>01</b>
            <span>Chụp mã vạch</span>
          </div>
          <div>
            <b>02</b>
            <span>Chấm điểm theo mục tiêu</span>
          </div>
          <div>
            <b>03</b>
            <span>Theo dõi &amp; lập kế hoạch</span>
          </div>
          <div>
            <b>04</b>
            <span>Xem phân tích sâu</span>
          </div>
        </section>
      </div>
    );
  }

  if (error)
    return <p className="error" style={{ padding: 20 }}>{error}</p>;
  if (!data)
    return <div className="loading-state">Đang tính toán thông tin dinh dưỡng…</div>;

  const riskData = Object.entries(data.risk_distribution).map(([name, value]) => ({ name, value }));

  return (
    <div className="page dashboard-page">
      {/* Header */}
      <div className="header">
        <div>
          <p className="eyebrow">Thông tin dinh dưỡng cá nhân</p>
          <h1>Chào lại, {user.display_name} 👋</h1>
          <p className="muted">Tổng quan về quyết định sản phẩm và tủ đồ của bạn.</p>
        </div>
        <Link className="button" href="/scan">
          <ScanLine size={16} />
          Quét sản phẩm
        </Link>
      </div>

      {/* Metrics */}
      <section className="metric-grid">
        {data.metrics.map((metric) => (
          <article className="metric" key={metric.label}>
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
            <small>{metric.detail}</small>
          </article>
        ))}
      </section>

      {/* Charts row */}
      <section className="dashboard-grid">
        <div className="card">
          <div className="section-heading" style={{ marginBottom: 16 }}>
            <div>
              <p className="eyebrow">Phân bố rủi ro</p>
              <h2 style={{ marginBottom: 0 }}>Sản phẩm đã quét</h2>
            </div>
          </div>

          {riskData.some((item) => item.value > 0) ? (
            <>
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie
                    data={riskData}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={60}
                    outerRadius={90}
                    paddingAngle={3}
                    strokeWidth={0}
                  >
                    {riskData.map((item) => (
                      <Cell key={item.name} fill={colors[item.name]} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(value, name) => [value, riskLabels[name as string] ?? name]}
                    contentStyle={{
                      background: "var(--panel-solid)",
                      border: "1px solid var(--line-solid)",
                      borderRadius: "var(--r)",
                      fontSize: 13,
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="legend">
                {riskData.map((item) => (
                  <span key={item.name}>
                    <i style={{ background: colors[item.name] }} />
                    {riskLabels[item.name] ?? item.name}&nbsp;
                    <strong style={{ color: "var(--ink)" }}>{item.value}</strong>
                  </span>
                ))}
              </div>
            </>
          ) : (
            <div className="empty-state" style={{ minHeight: 200 }}>
              <TrendingUp size={32} strokeWidth={1.5} style={{ marginBottom: 8, opacity: 0.4 }} />
              <p>Quét sản phẩm để xây dựng hồ sơ rủi ro.</p>
            </div>
          )}
        </div>

        <div className="card">
          <p className="eyebrow">Tín hiệu lặp lại</p>
          <h2>Cảnh báo hàng đầu</h2>
          {data.top_warnings.length ? (
            <ul className="rank-list">
              {data.top_warnings.map((item) => (
                <li key={item.warning}>
                  <span style={{ color: "var(--ink-2)", fontSize: 13 }}>{item.warning}</span>
                  <b>{item.count}</b>
                </li>
              ))}
            </ul>
          ) : (
            <div className="empty-state" style={{ minHeight: 120 }}>
              <Shield size={28} strokeWidth={1.5} style={{ marginBottom: 8, opacity: 0.4 }} />
              <p>Chưa có mẫu cảnh báo nào.</p>
            </div>
          )}
        </div>
      </section>

      {/* Recent scans */}
      <section className="card">
        <div className="section-heading" style={{ marginBottom: 12 }}>
          <div>
            <p className="eyebrow">Hoạt động gần đây</p>
            <h2 style={{ marginBottom: 0 }}>Lần quét mới nhất</h2>
          </div>
          <Link href="/scan">
            Xem máy quét <ArrowRight size={14} />
          </Link>
        </div>

        {data.recent_scans.length ? (
          <div className="activity-table">
            {data.recent_scans.map((scan) => (
              <Link
                href={`/product/${scan.barcode}`}
                key={`${scan.barcode}-${scan.created_at}`}
              >
                <span>
                  <b>{scan.product_name ?? scan.barcode}</b>
                  <small>{new Date(scan.created_at).toLocaleString("vi-VN")}</small>
                </span>
                <strong
                  className={`score-text score-${ScoreClass(scan.score)}`}
                >
                  {scan.score ?? "–"}
                </strong>
              </Link>
            ))}
          </div>
        ) : (
          <div className="empty-state" style={{ minHeight: 100 }}>
            <Zap size={28} strokeWidth={1.5} style={{ marginBottom: 8, opacity: 0.4 }} />
            <p>Các lần quét gần đây sẽ hiển thị ở đây.</p>
          </div>
        )}
      </section>
    </div>
  );
}
