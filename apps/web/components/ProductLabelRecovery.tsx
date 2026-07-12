"use client";

import { useRef, useState } from "react";
import { AlertTriangle, Check, FileText, ImageUp, LoaderCircle } from "lucide-react";
import { apiFetch, toUserMessage, type LabelExtraction, type Product } from "@/lib/api";

const NUTRIENT_FIELDS = [
  ["energy-kcal_100g", "Năng lượng", "kcal"],
  ["proteins_100g", "Protein", "g"],
  ["carbohydrates_100g", "Carbohydrate", "g"],
  ["sugars_100g", "Đường", "g"],
  ["fat_100g", "Chất béo", "g"],
  ["saturated-fat_100g", "Béo bão hòa", "g"],
  ["fiber_100g", "Chất xơ", "g"],
  ["sodium_100g", "Natri", "g"],
] as const;

type Props = {
  barcode: string;
  onConfirmed: () => void;
};

export function ProductLabelRecovery({ barcode, onConfirmed }: Props) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [extraction, setExtraction] = useState<LabelExtraction | null>(null);
  const [name, setName] = useState("");
  const [brand, setBrand] = useState("");
  const [ingredients, setIngredients] = useState("");
  const [allergens, setAllergens] = useState("");
  const [additives, setAdditives] = useState("");
  const [nutriments, setNutriments] = useState<Record<string, number>>({});
  const [processing, setProcessing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function processImage(file: File | undefined) {
    if (!file) return;
    setProcessing(true);
    setError(null);
    const body = new FormData();
    body.set("barcode", barcode);
    body.set("image", file);
    try {
      const result = await apiFetch<LabelExtraction>("/api/products/label-extractions", {
        method: "POST",
        body,
      });
      setExtraction(result);
      setIngredients(result.ingredients_text ?? "");
      setAllergens(result.allergens.join(", "));
      setAdditives(result.additives.join(", "));
      setNutriments(result.nutriments);
    } catch (err) {
      setError(toUserMessage(err, "Không thể đọc ảnh nhãn. Vui lòng thử ảnh rõ hơn."));
    } finally {
      setProcessing(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  async function confirm() {
    if (!extraction || !name.trim()) {
      setError("Vui lòng nhập tên sản phẩm trước khi xác nhận.");
      return;
    }
    setConfirming(true);
    setError(null);
    try {
      await apiFetch<Product>(`/api/products/label-extractions/${extraction.id}/confirm`, {
        method: "POST",
        body: JSON.stringify({
          name: name.trim(),
          brand: brand.trim() || null,
          ingredients_text: ingredients.trim() || null,
          allergens: splitTerms(allergens),
          additives: splitTerms(additives),
          nutriments,
        }),
      });
      onConfirmed();
    } catch (err) {
      setError(toUserMessage(err, "Không thể lưu dữ liệu nhãn. Vui lòng thử lại."));
    } finally {
      setConfirming(false);
    }
  }

  return (
    <section className="card label-recovery">
      <div className="label-recovery-heading">
        <div className="label-recovery-icon"><FileText size={20} /></div>
        <div>
          <p className="eyebrow">Bổ sung dữ liệu sản phẩm</p>
          <h2>Đọc thành phần từ nhãn bao bì</h2>
          <p className="muted">Chụp thẳng, đủ sáng và lấy trọn bảng thành phần hoặc dinh dưỡng.</p>
        </div>
      </div>

      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        capture="environment"
        hidden
        onChange={(event) => void processImage(event.target.files?.[0])}
      />
      <button className="button secondary" type="button" onClick={() => inputRef.current?.click()} disabled={processing}>
        {processing ? <LoaderCircle className="spin" size={16} /> : <ImageUp size={16} />}
        {processing ? "Đang đọc và phân tích…" : extraction ? "Đọc ảnh khác" : "Chụp hoặc tải ảnh nhãn"}
      </button>

      {extraction ? (
        <div className="label-review">
          <div className="toolbar">
            <span className="badge">Độ tin cậy {Math.round(extraction.confidence * 100)}%</span>
            <span className="muted">{extraction.ocr_provider} · {extraction.extractor_version}</span>
          </div>
          {extraction.validation_issues.length ? (
            <div className="label-warnings">
              <AlertTriangle size={17} />
              <div>{extraction.validation_issues.map((issue) => <p key={issue}>{issue}</p>)}</div>
            </div>
          ) : null}

          <div className="form-grid two">
            <label className="field"><span>Tên sản phẩm *</span><input value={name} onChange={(e) => setName(e.target.value)} /></label>
            <label className="field"><span>Thương hiệu</span><input value={brand} onChange={(e) => setBrand(e.target.value)} /></label>
          </div>
          <label className="field"><span>Thành phần</span><textarea rows={4} value={ingredients} onChange={(e) => setIngredients(e.target.value)} /></label>
          <div className="form-grid two">
            <label className="field"><span>Dị ứng, phân cách bằng dấu phẩy</span><input value={allergens} onChange={(e) => setAllergens(e.target.value)} /></label>
            <label className="field"><span>Phụ gia</span><input value={additives} onChange={(e) => setAdditives(e.target.value)} /></label>
          </div>

          <div>
            <h3>Dinh dưỡng trên 100 g/ml</h3>
            <div className="nutrient-review-grid">
              {NUTRIENT_FIELDS.map(([key, label, unit]) => (
                <label className="field" key={key}>
                  <span>{label} ({unit})</span>
                  <input
                    type="number"
                    min="0"
                    step="any"
                    value={nutriments[key] ?? ""}
                    onChange={(event) => setNutriments((current) => updateNumber(current, key, event.target.value))}
                  />
                </label>
              ))}
            </div>
          </div>
          <details><summary>Văn bản OCR gốc</summary><pre className="ocr-raw">{extraction.raw_text}</pre></details>
          <button className="button" type="button" onClick={() => void confirm()} disabled={confirming}>
            {confirming ? <LoaderCircle className="spin" size={16} /> : <Check size={16} />}
            {confirming ? "Đang lưu…" : "Xác nhận dữ liệu sản phẩm"}
          </button>
        </div>
      ) : null}
      {error ? <p className="error">{error}</p> : null}
    </section>
  );
}

function splitTerms(value: string): string[] {
  return value.split(",").map((term) => term.trim()).filter(Boolean);
}

function updateNumber(current: Record<string, number>, key: string, raw: string): Record<string, number> {
  const next = { ...current };
  if (raw === "") delete next[key];
  else next[key] = Number(raw);
  return next;
}
