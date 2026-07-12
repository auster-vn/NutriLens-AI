"use client";

import { useEffect, useRef, useState } from "react";
import { BrowserMultiFormatReader } from "@zxing/browser";
import { BarcodeFormat } from "@zxing/library";
import { Search, Video, VideoOff, Camera, History, ImageUp } from "lucide-react";
import Link from "next/link";
import { ApiError, apiFetch, toUserMessage, type ProductWithScore } from "@/lib/api";
import { ProductLabelRecovery } from "./ProductLabelRecovery";
import { ProductSummary } from "./ProductSummary";
import { ScanHistoryPanel } from "./ScanHistoryPanel";

export function BarcodeScanPanel() {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const controlsRef = useRef<{ stop: () => void } | null>(null);
  const imageInputRef = useRef<HTMLInputElement | null>(null);
  const [barcode, setBarcode] = useState("737628064502");
  const [barcodeFormat, setBarcodeFormat] = useState<string | null>(null);
  const [result, setResult] = useState<ProductWithScore | null>(null);
  const [loading, setLoading] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [decodingImage, setDecodingImage] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [historyVersion, setHistoryVersion] = useState(0);
  const [productMissing, setProductMissing] = useState(false);

  useEffect(() => () => controlsRef.current?.stop(), []);

  async function lookup(code = barcode, format = barcodeFormat) {
    setLoading(true);
    setError(null);
    setProductMissing(false);
    try {
      const data = await apiFetch<ProductWithScore>("/api/products/scan", {
        method: "POST",
        body: JSON.stringify({ barcode: code, barcode_format: format }),
      });
      setResult(data);
      setHistoryVersion((v) => v + 1);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) setProductMissing(true);
      setError(toUserMessage(err, "Không thể tra cứu mã vạch. Vui lòng thử lại."));
    } finally {
      setLoading(false);
    }
  }

  async function startCamera() {
    setError(null);
    setScanning(true);
    const reader = new BrowserMultiFormatReader();
    try {
      controlsRef.current = await reader.decodeFromConstraints(
        {
          audio: false,
          video: {
            facingMode: { ideal: "environment" },
            width: { ideal: 1280 },
            height: { ideal: 720 },
          },
        },
        videoRef.current!,
        (scanResult) => {
          if (scanResult) {
            const code = scanResult.getText();
            const format = BarcodeFormat[scanResult.getBarcodeFormat()];
            setBarcode(code);
            setBarcodeFormat(format);
            controlsRef.current?.stop();
            setScanning(false);
            void lookup(code, format);
          }
        }
      );
    } catch (err) {
      setScanning(false);
      setError(toUserMessage(err, "Camera không khả dụng trên thiết bị này."));
    }
  }

  async function scanImage(file: File | undefined) {
    if (!file) return;
    setError(null);
    setDecodingImage(true);
    try {
      const bitmap = await createImageBitmap(file);
      const maxSide = 1600;
      const scale = Math.min(1, maxSide / Math.max(bitmap.width, bitmap.height));
      const canvas = document.createElement("canvas");
      canvas.width = Math.max(1, Math.round(bitmap.width * scale));
      canvas.height = Math.max(1, Math.round(bitmap.height * scale));
      const context = canvas.getContext("2d", { willReadFrequently: true });
      try {
        if (!context) throw new Error("Canvas 2D is unavailable");
        context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
      } finally {
        bitmap.close();
      }

      const decoded = new BrowserMultiFormatReader().decodeFromCanvas(canvas);
      const code = decoded.getText();
      const format = BarcodeFormat[decoded.getBarcodeFormat()];
      setBarcode(code);
      setBarcodeFormat(format);
      await lookup(code, format);
    } catch (err) {
      setError(toUserMessage(err, "Không tìm thấy barcode rõ nét trong ảnh. Hãy chụp gần hơn và đủ sáng."));
    } finally {
      setDecodingImage(false);
      if (imageInputRef.current) imageInputRef.current.value = "";
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

          <input
            ref={imageInputRef}
            type="file"
            accept="image/*"
            capture="environment"
            hidden
            onChange={(event) => void scanImage(event.target.files?.[0])}
          />
          <button
            className="button secondary"
            type="button"
            onClick={() => imageInputRef.current?.click()}
            disabled={decodingImage || loading}
          >
            <ImageUp size={16} />
            {decodingImage ? "Đang đọc ảnh…" : "Đọc từ ảnh"}
          </button>

          <label className="field" style={{ flex: "1 1 200px" }}>
            <span>Mã vạch</span>
            <input
              value={barcode}
              onChange={(e) => { setBarcode(e.target.value); setBarcodeFormat(null); }}
              inputMode="text"
              placeholder="GTIN hoặc GS1 Digital Link..."
            />
          </label>

          <button
            className="button"
            type="button"
            onClick={() => lookup(barcode, barcodeFormat)}
            disabled={loading}
            style={{ alignSelf: "flex-end" }}
          >
            <Search size={16} />
            {loading ? "Đang tìm…" : "Tra cứu"}
          </button>
        </div>

        <div className="barcode-support-row">
          {barcodeFormat ? <span className="badge">Đã nhận diện: {barcodeFormat.replaceAll("_", "-")}</span> : null}
          <span className="muted">Hỗ trợ EAN, UPC, GTIN-14, Code 128/GS1, Data Matrix và GS1 QR.</span>
        </div>

        {error ? <p className="error">{error}</p> : null}
      </section>

      {productMissing ? (
        <ProductLabelRecovery
          barcode={barcode}
          onConfirmed={() => void lookup(barcode, barcodeFormat)}
        />
      ) : null}

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
