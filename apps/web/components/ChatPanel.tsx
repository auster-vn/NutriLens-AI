"use client";

import { useEffect, useState } from "react";
import { Send, Bot, User, Clock, BookOpen } from "lucide-react";
import { apiFetch } from "@/lib/api";

type ChatResult = {
  route: string;
  answer: string;
  citations: Array<{
    source: string;
    title: string;
    source_url?: string | null;
    snippet: string;
    chunk_id?: string | null;
    fused_score?: number | null;
  }>;
  abstained: boolean;
  disclaimer: string;
  retrieval_strategy: string;
  release_version?: string | null;
  retrieval_ms?: number | null;
};

type Message = {
  role: "user" | "assistant";
  content: string;
  route?: string;
  abstained?: boolean;
  citations?: ChatResult["citations"];
  retrievalStrategy?: string;
  releaseVersion?: string | null;
  retrievalMs?: number | null;
};

const suggestions = [
  "Đường cao trong sản phẩm nghĩa là gì?",
  "Chất bảo quản nào an toàn cho trẻ em?",
  "Sản phẩm ít natri là như thế nào?",
];

export function ChatPanel() {
  const [question, setQuestion] = useState("Đường cao trong sản phẩm nghĩa là gì?");
  const [barcode, setBarcode] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const linked = params.get("barcode");
    if (linked) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setBarcode(linked);
      setQuestion("Sản phẩm này có phù hợp với mục tiêu của tôi không?");
    }
  }, []);

  async function ask() {
    setError(null);
    const asked = question.trim();
    if (!asked) return;
    setLoading(true);
    setMessages((cur) => [...cur, { role: "user", content: asked }]);
    try {
      const result = await apiFetch<ChatResult>("/api/chat/stream", {
        method: "POST",
        body: JSON.stringify({ question: asked, barcode: barcode || null }),
      });
      setMessages((cur) => [
        ...cur,
        {
          role: "assistant",
          content: result.answer,
          route: result.route,
          abstained: result.abstained,
          citations: result.citations,
          retrievalStrategy: result.retrieval_strategy,
          releaseVersion: result.release_version,
          retrievalMs: result.retrieval_ms,
        },
      ]);
      setQuestion("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chat thất bại");
    } finally {
      setLoading(false);
    }
  }

  function handleKey(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) void ask();
  }

  return (
    <div className="page animate-slide-up">
      {/* Header */}
      <div className="header">
        <div>
          <p className="eyebrow">Trợ lý được trích dẫn</p>
          <h1>Hỏi về dinh dưỡng</h1>
          <p className="muted">
            Câu trả lời trích dẫn từ kho kiến thức đã được xác minh. AI sẽ từ chối khi không đủ bằng chứng.
          </p>
        </div>
      </div>

      {/* Input card */}
      <section className="card" style={{ display: "grid", gap: 14 }}>
        {/* Quick suggestions */}
        {messages.length === 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {suggestions.map((s) => (
              <button
                key={s}
                className="button secondary"
                style={{ fontSize: 12.5, minHeight: 30, padding: "0 12px" }}
                onClick={() => setQuestion(s)}
              >
                {s}
              </button>
            ))}
          </div>
        )}

        <label className="field">
          <span>Câu hỏi của bạn</span>
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Đặt câu hỏi về dinh dưỡng, thành phần, hoặc sản phẩm cụ thể…"
            style={{ minHeight: 80 }}
          />
        </label>

        <div className="toolbar" style={{ justifyContent: "space-between" }}>
          <label className="field" style={{ flex: "1 1 180px" }}>
            <span>Mã vạch sản phẩm (tuỳ chọn)</span>
            <input
              value={barcode}
              onChange={(e) => setBarcode(e.target.value)}
              placeholder="e.g. 737628064502"
            />
          </label>
          <button
            className="button"
            onClick={ask}
            disabled={loading || !question.trim()}
            style={{ alignSelf: "flex-end", minWidth: 110 }}
          >
            <Send size={15} />
            {loading ? "Đang hỏi…" : "Gửi câu hỏi"}
          </button>
        </div>

        <p className="muted" style={{ fontSize: 11.5, margin: 0 }}>
          Ctrl+Enter để gửi nhanh
        </p>

        {error ? <p className="error">{error}</p> : null}
      </section>

      {/* Messages */}
      <section style={{ display: "grid", gap: 12 }}>
        {messages.map((message, index) => (
          <article
            className={`card message ${message.role}`}
            key={`${message.role}-${index}`}
          >
            {/* Role header */}
            <div className="toolbar" style={{ marginBottom: 10, gap: 8 }}>
              <div style={{
                width: 30, height: 30, borderRadius: "50%",
                display: "grid", placeItems: "center",
                background: message.role === "user"
                  ? "rgba(59,130,246,0.12)"
                  : "rgba(16,185,129,0.12)",
                color: message.role === "user" ? "var(--blue)" : "var(--green)",
                flexShrink: 0,
              }}>
                {message.role === "user"
                  ? <User size={14} />
                  : <Bot size={14} />}
              </div>

              <span className="message-role-badge">
                {message.role === "user" ? "Bạn" : "NutriLens AI"}
              </span>

              {message.route ? (
                <span className="badge">
                  {message.route}{message.abstained ? " · từ chối" : ""}
                </span>
              ) : null}
              {message.retrievalMs != null ? (
                <span className="badge" style={{ background: "var(--bg-2)", color: "var(--muted)" }}>
                  <Clock size={10} style={{ marginRight: 3 }} />
                  {message.retrievalMs} ms
                </span>
              ) : null}
            </div>

            {/* Content */}
            <p style={{ margin: 0, fontSize: 14, lineHeight: 1.7, color: "var(--ink-2)" }}>
              {message.content}
            </p>

            {/* Citations */}
            {message.citations?.length ? (
              <div style={{ marginTop: 16 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
                  <BookOpen size={13} style={{ color: "var(--green)" }} />
                  <h3 style={{ margin: 0, fontSize: 12, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.07em", color: "var(--muted)" }}>
                    Nguồn trích dẫn
                  </h3>
                </div>
                <ul className="list">
                  {message.citations.map((citation) => (
                    <li key={`${citation.source}-${citation.chunk_id ?? "doc"}`}>
                      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 10 }}>
                        <strong style={{ fontSize: 13, lineHeight: 1.4 }}>{citation.title}</strong>
                        <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
                          {citation.fused_score != null ? (
                            <span className="badge">RRF {citation.fused_score.toFixed(4)}</span>
                          ) : null}
                          {citation.source_url ? (
                            <a
                              className="badge"
                              href={citation.source_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              style={{ textDecoration: "none", cursor: "pointer" }}
                            >
                              Nguồn ↗
                            </a>
                          ) : null}
                        </div>
                      </div>
                      <p className="muted" style={{ marginTop: 4, marginBottom: 0, fontSize: 12.5, lineHeight: 1.6 }}>
                        {citation.snippet}
                      </p>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </article>
        ))}

        {loading ? (
          <div className="card" style={{ padding: "20px", display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{ width: 30, height: 30, borderRadius: "50%", background: "var(--green-light)", display: "grid", placeItems: "center", color: "var(--green)" }}>
              <Bot size={14} />
            </div>
            <p className="muted" style={{ margin: 0, fontSize: 13 }}>
              NutriLens AI đang truy xuất kiến thức…
            </p>
          </div>
        ) : null}
      </section>
    </div>
  );
}
