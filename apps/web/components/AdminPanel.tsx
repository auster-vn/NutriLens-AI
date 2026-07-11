"use client";

import { useState } from "react";
import { Database, FileText, Play, RefreshCw, RotateCcw, Trash2, Upload } from "lucide-react";
import { API_BASE } from "@/lib/api";

const defaultMetadata = {
  authority: "editorial synthesis",
  source_url: "https://example.com",
  jurisdiction: "global",
  risk_level: "health",
  effective_from: "2026-01-01",
  expires_at: "2027-01-01",
  reviewed_at: "2026-07-10",
  evidence_level: "secondary",
  domains: ["nutrition"],
  status: "approved"
};

type AdminDocument = {
  id: string;
  filename: string;
  title: string;
  metadata: Record<string, unknown>;
  content: string;
  status: string;
};

type AuditRow = {
  id: string;
  operation: string;
  payload: Record<string, unknown>;
  created_at: string;
};

export function AdminPanel() {
  const [activeTab, setActiveTab] = useState<"upload" | "documents" | "audit" | "data">("upload");
  const [adminKey, setAdminKey] = useState("dev-admin-key");
  const [filename, setFilename] = useState("custom_guidance.md");
  const [title, setTitle] = useState("Custom Guidance");
  const [metadata, setMetadata] = useState(JSON.stringify(defaultMetadata, null, 2));
  const [content, setContent] = useState("# Custom Guidance\n\nApproved nutrition guidance goes here.");
  const [documents, setDocuments] = useState<AdminDocument[]>([]);
  const [selectedDocument, setSelectedDocument] = useState<AdminDocument | null>(null);
  const [audit, setAudit] = useState<AuditRow[]>([]);
  const [message, setMessage] = useState("");
  const [releases, setReleases] = useState<Array<Record<string, unknown>>>([]);
  const [pipelineRuns, setPipelineRuns] = useState<Array<Record<string, unknown>>>([]);
  const [evaluationRuns, setEvaluationRuns] = useState<Array<Record<string, unknown>>>([]);
  const [quality, setQuality] = useState<Record<string, unknown> | null>(null);
  const [observability, setObservability] = useState<Record<string, Record<string, unknown>> | null>(null);
  const [analytics, setAnalytics] = useState<Record<string, unknown> | null>(null);

  const headers = { "Content-Type": "application/json", "X-Admin-Key": adminKey };

  async function upload() {
    setMessage("");
    try {
      const response = await fetch(`${API_BASE}/api/admin/documents`, {
        method: "POST",
        headers,
        body: JSON.stringify({ filename, title, metadata: JSON.parse(metadata), content })
      });
      setMessage(response.ok ? "Uploaded and audited" : await response.text());
      if (response.ok) {
        await loadDocuments();
        setActiveTab("documents");
      }
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Upload failed");
    }
  }

  async function loadDocuments() {
    const response = await fetch(`${API_BASE}/api/admin/documents`, { headers });
    if (!response.ok) {
      setMessage(await response.text());
      return;
    }
    const rows = (await response.json()) as AdminDocument[];
    setDocuments(rows);
    setSelectedDocument(rows[0] ?? null);
  }

  async function loadAudit() {
    const response = await fetch(`${API_BASE}/api/admin/audit`, { headers });
    if (!response.ok) {
      setMessage(await response.text());
      return;
    }
    setAudit((await response.json()) as AuditRow[]);
  }

  async function deleteDocument(document: AdminDocument) {
    if (!confirm(`Delete ${document.filename}?`)) {
      return;
    }
    const response = await fetch(`${API_BASE}/api/admin/documents/${document.id}`, {
      method: "DELETE",
      headers
    });
    setMessage(response.ok ? "Deleted" : await response.text());
    await loadDocuments();
  }

  async function adminJson(path: string, init?: RequestInit) {
    const response = await fetch(`${API_BASE}${path}`, { ...init, headers });
    if (!response.ok) throw new Error(await response.text());
    return response.status === 204 ? null : response.json();
  }

  async function loadDataOps() {
    setMessage("");
    try {
      const [releaseRows, pipelineRows, evaluationRows, qualityReport, observabilitySnapshot, analyticsMarts] = await Promise.all([
        adminJson("/api/admin/rag/releases"),
        adminJson("/api/admin/data/pipeline-runs"),
        adminJson("/api/admin/evaluation/runs"),
        adminJson("/api/admin/data/quality"),
        adminJson("/api/admin/observability"),
        adminJson("/api/admin/analytics/marts")
      ]);
      setReleases(releaseRows);
      setPipelineRuns(pipelineRows);
      setEvaluationRuns(evaluationRows);
      setQuality(qualityReport);
      setObservability(observabilitySnapshot);
      setAnalytics(analyticsMarts);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Data operations failed");
    }
  }

  async function runOperation(path: string, body?: object) {
    setMessage("");
    try {
      await adminJson(path, { method: "POST", body: body ? JSON.stringify(body) : undefined });
      await loadDataOps();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Operation failed");
    }
  }

  return (
    <div className="page">
      <div>
        <p className="eyebrow">Admin studio</p>
        <h1>Manage approved knowledge</h1>
        <p className="muted">Upload, preview, delete, and audit knowledge documents.</p>
      </div>
      <section className="card grid">
        <label className="field">
          <span>Admin key</span>
          <input type="password" value={adminKey} onChange={(event) => setAdminKey(event.target.value)} />
        </label>
        <div className="toolbar">
          <button className={`button ${activeTab === "upload" ? "" : "secondary"}`} onClick={() => setActiveTab("upload")}>
            <Upload size={18} />Upload
          </button>
          <button className={`button ${activeTab === "documents" ? "" : "secondary"}`} onClick={() => { setActiveTab("documents"); void loadDocuments(); }}>
            <FileText size={18} />Documents
          </button>
          <button className={`button ${activeTab === "audit" ? "" : "secondary"}`} onClick={() => { setActiveTab("audit"); void loadAudit(); }}>
            <RefreshCw size={18} />Audit
          </button>
          <button className={`button ${activeTab === "data" ? "" : "secondary"}`} onClick={() => { setActiveTab("data"); void loadDataOps(); }}>
            <Database size={18} />Data Ops
          </button>
        </div>
        {message ? <p className={message.startsWith("{") ? "error" : "muted"}>{message}</p> : null}
      </section>

      {activeTab === "upload" ? (
        <section className="card grid">
          <div className="grid two">
            <label className="field"><span>Filename</span><input value={filename} onChange={(event) => setFilename(event.target.value)} /></label>
            <label className="field"><span>Title</span><input value={title} onChange={(event) => setTitle(event.target.value)} /></label>
          </div>
          <label className="field"><span>Metadata JSON</span><textarea value={metadata} onChange={(event) => setMetadata(event.target.value)} /></label>
          <label className="field"><span>Markdown content</span><textarea value={content} onChange={(event) => setContent(event.target.value)} /></label>
          <button className="button" onClick={upload}><Upload size={18} />Upload document</button>
        </section>
      ) : null}

      {activeTab === "documents" ? (
        <section className="grid two">
          <div className="card">
            <div className="toolbar" style={{ justifyContent: "space-between" }}>
              <h2>Documents</h2>
              <button className="button secondary" onClick={loadDocuments}><RefreshCw size={16} />Refresh</button>
            </div>
            <ul className="list">
              {documents.map((document) => (
                <li key={document.id}>
                  <button className="link-button" onClick={() => setSelectedDocument(document)}>
                    <strong>{document.title}</strong>
                    <span className="muted">{document.filename} · {document.status}</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
          <div className="card">
            {selectedDocument ? (
              <>
                <div className="toolbar" style={{ justifyContent: "space-between" }}>
                  <h2>{selectedDocument.title}</h2>
                  <button className="button secondary" title="Delete" onClick={() => deleteDocument(selectedDocument)}><Trash2 size={16} /></button>
                </div>
                <span className="badge">{selectedDocument.status}</span>
                <h3>Metadata</h3>
                <pre className="code-block">{JSON.stringify(selectedDocument.metadata, null, 2)}</pre>
                <h3>Preview</h3>
                <pre className="code-block">{selectedDocument.content}</pre>
              </>
            ) : <p className="muted">No document selected.</p>}
          </div>
        </section>
      ) : null}

      {activeTab === "audit" ? (
        <section className="card">
          <div className="toolbar" style={{ justifyContent: "space-between" }}>
            <h2>Audit log</h2>
            <button className="button secondary" onClick={loadAudit}><RefreshCw size={16} />Refresh</button>
          </div>
          <table className="table">
            <thead><tr><th>Operation</th><th>Payload</th><th>Time</th></tr></thead>
            <tbody>
              {audit.map((row) => (
                <tr key={row.id}>
                  <td>{row.operation}</td>
                  <td><code>{JSON.stringify(row.payload)}</code></td>
                  <td>{new Date(row.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ) : null}

      {activeTab === "data" ? (
        <section className="grid">
          <div className="card toolbar">
            <button className="button" onClick={() => void runOperation("/api/admin/data/run-pipeline")}><Play size={17} />Run release pipeline</button>
            <button className="button secondary" onClick={() => void runOperation("/api/admin/evaluate")}><Play size={17} />Run evaluation</button>
            <button className="button secondary" onClick={() => void runOperation("/api/admin/rag/rollback")}><RotateCcw size={17} />Rollback</button>
            <button className="icon-button" title="Refresh data operations" onClick={() => void loadDataOps()}><RefreshCw size={17} /></button>
          </div>
          <div className="metric-grid">
            <article className="metric"><span>RAG answers</span><strong>{String(observability?.rag?.answer_count ?? 0)}</strong><small>audited requests</small></article>
            <article className="metric"><span>Mean latency</span><strong>{String(observability?.rag?.latency_mean_ms ?? 0)}</strong><small>milliseconds</small></article>
            <article className="metric"><span>Citation coverage</span><strong>{Math.round(Number(observability?.rag?.citation_coverage ?? 0) * 100)}%</strong><small>grounded answers</small></article>
            <article className="metric"><span>Pipeline failures</span><strong>{String(observability?.pipelines?.failed_or_blocked_count ?? 0)}</strong><small>failed or blocked</small></article>
          </div>
          <div className="grid two">
            <article className="card"><p className="eyebrow">Knowledge registry</p><h2>Releases</h2><pre className="code-block">{JSON.stringify(releases.slice(0, 5), null, 2)}</pre></article>
            <article className="card"><p className="eyebrow">Data observability</p><h2>Quality report</h2><pre className="code-block">{JSON.stringify(quality, null, 2)}</pre></article>
            <article className="card"><p className="eyebrow">Lineage</p><h2>Pipeline runs</h2><pre className="code-block">{JSON.stringify(pipelineRuns.slice(0, 5), null, 2)}</pre></article>
            <article className="card"><p className="eyebrow">RAG benchmark</p><h2>Evaluation runs</h2><pre className="code-block">{JSON.stringify(evaluationRuns.slice(0, 5), null, 2)}</pre></article>
            <article className="card"><p className="eyebrow">Analytics layer</p><h2>Product and AI marts</h2><pre className="code-block">{JSON.stringify(analytics, null, 2)}</pre></article>
          </div>
        </section>
      ) : null}
    </div>
  );
}
