"use client";

import { useEffect, useState } from "react";
import { Send } from "lucide-react";
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

export function ChatPanel() {
  const [question, setQuestion] = useState("Đường cao trong sản phẩm nghĩa là gì?");
  const [barcode, setBarcode] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const linkedBarcode = params.get("barcode");
    if (linkedBarcode) {
      // Hydrate optional deep-link state from the current URL.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setBarcode(linkedBarcode);
      setQuestion("Sản phẩm này có phù hợp với mục tiêu của tôi không?");
    }
  }, []);

  async function ask() {
    setError(null);
    const asked = question.trim();
    if (!asked) {
      return;
    }
    setLoading(true);
    setMessages((current) => [...current, { role: "user", content: asked }]);
    try {
      const result = await apiFetch<ChatResult>("/api/chat/stream", {
        method: "POST",
        body: JSON.stringify({ question: asked, barcode: barcode || null })
      });
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: result.answer,
          route: result.route,
          abstained: result.abstained,
          citations: result.citations,
          retrievalStrategy: result.retrieval_strategy,
          releaseVersion: result.release_version,
          retrievalMs: result.retrieval_ms
        }
      ]);
      setQuestion("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chat failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page">
      <div>
        <p className="eyebrow">Grounded assistant</p>
        <h1>Ask nutrition questions</h1>
        <p className="muted">Answers cite the local approved corpus and abstain when there is not enough evidence.</p>
      </div>
      <section className="card grid">
        <label className="field"><span>Question</span><textarea value={question} onChange={(event) => setQuestion(event.target.value)} /></label>
        <label className="field"><span>Optional product barcode</span><input value={barcode} onChange={(event) => setBarcode(event.target.value)} /></label>
        <button className="button" onClick={ask} disabled={loading}><Send size={18} />{loading ? "Asking" : "Ask"}</button>
        {error ? <p className="error">{error}</p> : null}
      </section>
      <section className="grid">
        {messages.map((message, index) => (
          <article className={`card message ${message.role}`} key={`${message.role}-${index}`}>
            <div className="toolbar">
              <span className="badge">{message.role}</span>
              {message.route ? <span className="badge">{message.route}{message.abstained ? " · abstained" : ""}</span> : null}
              {message.retrievalStrategy ? <span className="badge">{message.retrievalStrategy}</span> : null}
              {message.releaseVersion ? <span className="badge">release {message.releaseVersion}</span> : null}
              {message.retrievalMs != null ? <span className="badge">{message.retrievalMs} ms</span> : null}
            </div>
            <p style={{ marginTop: 12 }}>{message.content}</p>
            {message.citations?.length ? (
              <>
                <h3>Citations</h3>
                <ul className="list">
                  {message.citations.map((citation) => (
                    <li key={`${citation.source}-${citation.chunk_id ?? "document"}`}>
                      <strong>{citation.title}</strong>
                      {citation.fused_score != null ? <span className="badge">RRF {citation.fused_score.toFixed(5)}</span> : null}
                      <p className="muted">{citation.snippet}</p>
                      {citation.source_url ? <a className="badge" href={citation.source_url} target="_blank">Source</a> : null}
                    </li>
                  ))}
                </ul>
              </>
            ) : null}
          </article>
        ))}
      </section>
    </div>
  );
}
