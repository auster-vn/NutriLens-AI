"use client";

import { useEffect, useRef, useState } from "react";
import { BrowserMultiFormatReader } from "@zxing/browser";
import { Search, Video, VideoOff, Camera, History } from "lucide-react";
import Link from "next/link";
import { apiFetch, type ProductWithScore } from "@/lib/api";
import { ProductSummary } from "./ProductSummary";
import { ScanHistoryPanel } from "./ScanHistoryPanel";

export function BarcodeScanPanel() {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const controlsRef = useRef<{ stop: () => void } | null>(null);
  const [barcode, setBarcode] = useState("737628064502");
  const [result, setResult] = useState<ProductWithScore | null>(null);
  const [loading, setLoading] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [historyVersion, setHistoryVersion] = useState(0);

  useEffect(() => () => controlsRef.current?.stop(), []);

  async function lookup(code = barcode) {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<ProductWithScore>("/api/products/scan", {
        method: "POST",
        body: JSON.stringify({ barcode: code }),
      });
      setResult(data);
      setHistoryVersion((v) => v + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Quét thất bại");
    } finally {
      setLoading(false);
    }
  }

  async function startCamera() {
    setError(null);
    setScanning(true);
    const reader = new BrowserMultiFormatReader();
    try {
      controlsRef.current = await reader.decodeFromVideoDevice(
        undefined,
        videoRef.current!,
        (scanResult) => {
          if (scanResult) {
            const code = scanResult.getText();
            setBarcode(code);
            controlsRef.current?.stop();
            setScanning(false);
            void lookup(code);
          }
        }
      );
    } catch (err) {
      setScanning(false);
      setError(err instanceof Error ? err.message : "Camera không khả dụng");
    }
  }

  function stopCamera() {
    controlsRef.current?.stop();
    setScanning(false);
  }

  return (
    <div className="page animate-slide-up">
      {/* Header */}
      <div className="header">
        <div>
          <p className="eyebrow">Máy quét mã vạch</p>
          <h1>Quét hoặc nhập mã vạch</h1>
          <p className="muted">
            Camera quét trực tiếp trên trình duyệt, hoặc nhập thủ công để tra cứu.
          </p>
        </div>
      </div>

      {/* Scanner card */}
      <section className="card" style={{ display: "grid", gap: 16 }}>
        {/* Camera viewport */}
        <div className="camera">
          <video ref={videoRef} muted playsInline style={{ borderRadius: "var(--r)" }} />
          {!scanning ? (
            <div style={{ textAlign: "center", padding: 24 }}>
              <Camera
                size={40}
                strokeWidth={1.2}
                style={{ color: "var(--muted-2)", marginBottom: 8 }}
              />
              <p className="muted" style={{ margin: 0, fontSize: 13 }}>
                Nhấn &ldquo;Camera&rdquo; để bật camera và quét mã vạch
              </p>
            </div>
          ) : null}
        </div>

        {/* Toolbar */}
        <div className="toolbar">
          <button
            className="button secondary"
            type="button"
            onClick={scanning ? stopCamera : startCamera}
          >
            {scanning ? <VideoOff size={16} /> : <Video size={16} />}
            {scanning ? "Dừng camera" : "Bật camera"}
          </button>

          <label className="field" style={{ flex: "1 1 200px" }}>
            <span>Mã vạch</span>
            <input
              value={barcode}
              onChange={(e) => setBarcode(e.target.value)}
              inputMode="numeric"
              placeholder="Nhập mã vạch..."
            />
          </label>

          <button
            className="button"
            type="button"
            onClick={() => lookup()}
            disabled={loading}
            style={{ alignSelf: "flex-end" }}
          >
            <Search size={16} />
            {loading ? "Đang tìm…" : "Tra cứu"}
          </button>
        </div>

        {error ? <p className="error">{error}</p> : null}
      </section>

      {/* Result */}
      {result ? (
        <>
          <section
            className="card toolbar"
            style={{ justifyContent: "space-between", background: "var(--green-light)", borderColor: "rgba(16,185,129,0.25)" }}
          >
            <div>
              <p className="eyebrow" style={{ marginBottom: 2 }}>Quét hoàn tất</p>
              <p style={{ margin: 0, fontSize: 13.5, fontWeight: 500, color: "var(--ink-2)" }}>
                Mở trang chi tiết để xem pantry, so sánh và chat với AI.
              </p>
            </div>
            <Link className="button" href={`/product/${result.product.barcode}`}>
              Xem chi tiết
            </Link>
          </section>
          <ProductSummary data={result} />
        </>
      ) : null}

      {/* History */}
      <section className="card">
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
          <History size={16} style={{ color: "var(--green)" }} />
          <h2 style={{ margin: 0 }}>Lịch sử quét</h2>
        </div>
        <ScanHistoryPanel refreshKey={historyVersion} />
      </section>
    </div>
  );
}
