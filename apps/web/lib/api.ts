export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? (process.env.NODE_ENV === "production" ? "" : "http://localhost:8000");

export type UserProfile = {
  age_group?: string | null;
  goal: string;
  allergies: string[];
  diet?: string | null;
  disliked_ingredients: string[];
  budget_daily?: number | null;
};

export type Product = {
  barcode: string;
  name?: string | null;
  brand?: string | null;
  categories: string[];
  ingredients_text?: string | null;
  allergens: string[];
  additives: string[];
  nutriments: Record<string, unknown>;
  nutriscore?: string | null;
  ecoscore?: string | null;
  image_url?: string | null;
  source: string;
  completeness_score?: number | null;
};

export type ProductScore = {
  score: number;
  label: string;
  risk_level: string;
  warnings: string[];
  good_points: string[];
  missing_data: string[];
  disclaimer: string;
};

export type ProductWithScore = {
  product: Product;
  score: ProductScore;
};

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    credentials: "include",
    cache: "no-store"
  });
  if (!response.ok) {
    const contentType = response.headers.get("content-type") ?? "";
    const payload = contentType.includes("application/json") ? await response.json() : await response.text();
    const detail = typeof payload === "object" && payload && "detail" in payload ? payload.detail : payload;
    const message = typeof detail === "string" ? detail : JSON.stringify(detail || response.statusText);
    throw new ApiError(message, response.status);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const defaultProfile: UserProfile = {
  goal: "general",
  allergies: [],
  disliked_ingredients: []
};
