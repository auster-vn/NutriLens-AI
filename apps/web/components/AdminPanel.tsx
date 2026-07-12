"use client";

import { useState } from "react";
import { Database, FileText, Play, RefreshCw, RotateCcw, ScanText, Trash2, Upload } from "lucide-react";
import { apiFetch, toUserMessage } from "@/lib/api";

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
  const [activeTab, setActiveTab] = useState<"upload" | "documents" | "audit" | "data" | "ocr">("upload");
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
  const [ocrDashboard, setOcrDashboard] = useState<Record<string, unknown> | null>(null);

  const headers = { "X-Admin-Key": adminKey };

  async function upload() {
    setMessage("");
    try {
      await apiFetch<AdminDocument>("/api/admin/documents", {
        method: "POST",
        headers,
        body: JSON.stringify({ filename, title, metadata: JSON.parse(metadata), content })
      });
      setMessage("Tài liệu đã được tải lên và ghi audit.");
      await loadDocuments();
      setActiveTab("documents");
    } catch (err) {
      setMessage(toUserMessage(err, "Không thể tải tài liệu lên."));
    }
  }

  async function loadDocuments() {
    try {
      const rows = await apiFetch<AdminDocument[]>("/api/admin/documents", { headers });
      setDocuments(rows);
      setSelectedDocument(rows[0] ?? null);
    } catch (err) {
      setMessage(toUserMessage(err, "Không thể tải danh sách tài liệu."));
    }
  }

  async function loadAudit() {
    try {
      setAudit(await apiFetch<AuditRow[]>("/api/admin/audit", { headers }));
    } catch (err) {
      setMessage(toUserMessage(err, "Không thể tải nhật ký quản trị."));
    }
  }

  async function deleteDocument(document: AdminDocument) {
    if (!confirm(`Delete ${document.filename}?`)) {
      return;
    }
    try {
      await apiFetch<void>(`/api/admin/documents/${document.id}`, {
      method: "DELETE",
      headers
      });
      setMessage("Đã xóa tài liệu.");
      await loadDocuments();
    } catch (err) {
      setMessage(toUserMessage(err, "Không thể xóa tài liệu."));
    }
  }

  async function adminJson<T>(path: string, init?: RequestInit): Promise<T> {
    return apiFetch<T>(path, { ...init, headers });
  }

  async function loadDataOps() {
    setMessage("");
    try {
      const [releaseRows, pipelineRows, evaluationRows, qualityReport, observabilitySnapshot, analyticsMarts] = await Promise.all([
        adminJson<Array<Record<string, unknown>>>("/api/admin/rag/releases"),
        adminJson<Array<Record<string, unknown>>>("/api/admin/data/pipeline-runs"),
        adminJson<Array<Record<string, unknown>>>("/api/admin/evaluation/runs"),
        adminJson<Record<string, unknown>>("/api/admin/data/quality"),
        adminJson<Record<string, Record<string, unknown>>>("/api/admin/observability"),
        adminJson<Record<string, unknown>>("/api/admin/analytics/marts")
      ]);
      setReleases(releaseRows);
      setPipelineRuns(pipelineRows);
      setEvaluationRuns(evaluationRows);
      setQuality(qualityReport);
      setObservability(observabilitySnapshot);
      setAnalytics(analyticsMarts);
    } catch (err) {
      setMessage(toUserMessage(err, "Không thể tải dữ liệu vận hành."));
    }
  }

  async function runOperation(path: string, body?: object) {
    setMessage("");
    try {
      await adminJson<unknown>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined });
      await loadDataOps();
    } catch (err) {
      setMessage(toUserMessage(err, "Không thể thực hiện thao tác quản trị."));
    }
  }

  async function loadOcrDashboard() {
    setMessage("");
    try {
      setOcrDashboard(await adminJson<Record<string, unknown>>("/api/admin/label-ocr/dashboard"));
    } catch (err) {
      setMessage(toUserMessage(err, "Không thể tải dashboard OCR."));
    }
  }

  async function runOcrEvaluation() {
    setMessage("");
    try {
      await adminJson("/api/admin/label-ocr/evaluate", { method: "POST" });
      await loadOcrDashboard();
    } catch (err) {
      setMessage(toUserMessage(err, "Không thể chạy benchmark OCR."));
    }
  }

  const latestOcr = ocrDashboard?.latest_evaluation as Record<string, unknown> | null | undefined;
  const ocrMetrics = latestOcr?.metrics as Record<string, unknown> | undefined;
  const ocrReadiness = latestOcr?.readiness as Record<string, unknown> | undefined;
  const ocrProduction = ocrDashboard?.production as Record<string, unknown> | undefined;

  return (
    <div className="admin-page">
      <div className="admin-heading">
        <p className="eyebrow">Admin studio</p>
        <h1>Knowledge & Data Control Plane</h1>
        <p className="muted">Quản trị corpus, release, evaluation gate, pipeline lineage và health metrics tại một khu vực độc lập.</p>
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
          <button className={`button ${activeTab === "ocr" ? "" : "secondary"}`} onClick={() => { setActiveTab("ocr"); void loadOcrDashboard(); }}>
            <ScanText size={18} />OCR Evaluation
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

      {activeTab === "ocr" ? (
        <section className="grid">
          <div className="card toolbar">
            <button className="button" onClick={() => void runOcrEvaluation()}><Play size={17} />Run OCR benchmark</button>
            <button className="icon-button" title="Refresh OCR dashboard" onClick={() => void loadOcrDashboard()}><RefreshCw size={17} /></button>
          </div>
          <div className="metric-grid">
            <article className="metric"><span>Production extractions</span><strong>{String(ocrProduction?.extraction_count ?? 0)}</strong><small>{String(ocrProduction?.confirmed_count ?? 0)} confirmed</small></article>
            <article className="metric"><span>Field F1</span><strong>{Math.round(Number(ocrMetrics?.field_f1 ?? 0) * 100)}%</strong><small>structured extraction</small></article>
            <article className="metric"><span>Numeric accuracy</span><strong>{Math.round(Number(ocrMetrics?.numeric_accuracy ?? 0) * 100)}%</strong><small>2% tolerance</small></article>
            <article className="metric"><span>Allergen recall</span><strong>{Math.round(Number(ocrMetrics?.allergen_recall ?? 0) * 100)}%</strong><small>safety-critical metric</small></article>
          </div>
          <div className="grid two">
            <article className="card">
              <p className="eyebrow">Provider benchmark</p>
              <h2>Character error rate</h2>
              <pre className="code-block">{JSON.stringify({
                labeledHypotheses: ocrMetrics?.provider_cer ?? {},
                runtimeImages: ocrMetrics?.runtime_provider_cer ?? {}
              }, null, 2)}</pre>
            </article>
            <article className="card">
              <p className="eyebrow">Model readiness gate</p>
              <h2>{ocrReadiness?.layoutlm_or_ner_ready ? "Ready for LayoutLMv3 / NER" : "Collect more labeled data"}</h2>
              <pre className="code-block">{JSON.stringify(ocrReadiness ?? {}, null, 2)}</pre>
            </article>
            <article className="card">
              <p className="eyebrow">Production quality</p>
              <h2>OCR pipeline telemetry</h2>
              <pre className="code-block">{JSON.stringify(ocrProduction ?? {}, null, 2)}</pre>
            </article>
            <article className="card">
              <p className="eyebrow">Case analysis</p>
              <h2>Latest benchmark run</h2>
              <pre className="code-block">{JSON.stringify((latestOcr?.case_results as unknown[] | undefined)?.slice(0, 8) ?? [], null, 2)}</pre>
            </article>
          </div>
        </section>
      ) : null}
    </div>
  );
}
