"use client";

import { useEffect, useRef, useState } from "react";
import { BrowserMultiFormatReader } from "@zxing/browser";
import { Search, Video, VideoOff } from "lucide-react";
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
        body: JSON.stringify({ barcode: code })
      });
      setResult(data);
      setHistoryVersion((current) => current + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Scan failed");
    } finally {
      setLoading(false);
    }
  }

  async function startCamera() {
    setError(null);
    setScanning(true);
    const reader = new BrowserMultiFormatReader();
    try {
      controlsRef.current = await reader.decodeFromVideoDevice(undefined, videoRef.current!, (scanResult) => {
        if (scanResult) {
          const code = scanResult.getText();
          setBarcode(code);
          controlsRef.current?.stop();
          setScanning(false);
          void lookup(code);
        }
      });
    } catch (err) {
      setScanning(false);
      setError(err instanceof Error ? err.message : "Camera unavailable");
    }
  }

  function stopCamera() {
    controlsRef.current?.stop();
    setScanning(false);
  }

  return (
    <div className="page">
      <div className="header">
        <div>
          <p className="eyebrow">Barcode scanner</p>
          <h1>Scan or enter a barcode</h1>
          <p className="muted">Camera uses browser scanning when available, with manual input as the reliable fallback.</p>
        </div>
      </div>
      <section className="card grid">
        <div className="camera">
          <video ref={videoRef} muted playsInline />
          {!scanning ? <p className="muted">Camera preview appears here.</p> : null}
        </div>
        <div className="toolbar">
          <button className="button secondary" type="button" onClick={scanning ? stopCamera : startCamera}>
            {scanning ? <VideoOff size={18} /> : <Video size={18} />}
            {scanning ? "Stop" : "Camera"}
          </button>
          <label className="field" style={{ flex: "1 1 220px" }}>
            <span>Barcode</span>
            <input value={barcode} onChange={(event) => setBarcode(event.target.value)} inputMode="numeric" />
          </label>
          <button className="button" type="button" onClick={() => lookup()} disabled={loading}>
            <Search size={18} />
            {loading ? "Loading" : "Lookup"}
          </button>
        </div>
        {error ? <p className="error">{error}</p> : null}
      </section>
      {result ? (
        <>
          <section className="card toolbar" style={{ justifyContent: "space-between" }}>
            <div>
              <h2>Scan complete</h2>
              <p className="muted">Open the full detail page for pantry, compare, and chat actions.</p>
            </div>
            <Link className="button" href={`/product/${result.product.barcode}`}>Open detail</Link>
          </section>
          <ProductSummary data={result} />
        </>
      ) : null}
      <ScanHistoryPanel refreshKey={historyVersion} />
    </div>
  );
}
