export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? (process.env.NODE_ENV === "production" ? "" : "http://localhost:8000");

export type UserProfile = {
  age_group?: string | null;
  goal: string;
  allergies: string[];
  diet?: string | null;
  disliked_ingredients: string[];
  budget_daily?: number | null;
  biological_sex?: "male" | "female" | null;
  age?: number | null;
  height_cm?: number | null;
  weight_kg?: number | null;
  activity_level?: "sedentary" | "light" | "moderate" | "very_active" | "extra_active" | null;
  target_weight_loss_kg_week?: number | null;
};

export type TdeeResult = {
  bmr_kcal: number;
  tdee_kcal: number;
  requested_deficit_kcal: number;
  recommended_deficit_kcal: number;
  target_calories_kcal: number;
  maintenance_range_kcal: [number, number];
  recommended_loss_kg_week: number;
  activity_factor: number;
  warnings: string[];
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

export type LabelExtraction = {
  id: string;
  barcode: string;
  status: string;
  raw_text: string;
  ingredients_text?: string | null;
  allergens: string[];
  additives: string[];
  nutriments: Record<string, number>;
  confidence: number;
  validation_issues: string[];
  ocr_provider: string;
  extractor_version: string;
  words: Array<Record<string, unknown>>;
  preprocessing: Record<string, unknown>;
  provider_runs: Array<Record<string, unknown>>;
  blocks: Array<Record<string, unknown>>;
  fields: Record<string, Record<string, unknown>>;
  ingredient_entities: Array<Record<string, unknown>>;
};

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code: string = "API_ERROR",
    readonly requestId: string | null = null,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const DETAIL_MESSAGES: Record<string, string> = {
  "Invalid email or password.": "Email hoặc mật khẩu không đúng.",
  "Authentication required.": "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.",
  "An account with this email already exists.": "Email này đã được sử dụng. Vui lòng đăng nhập hoặc chọn email khác.",
  "Admin authentication required.": "Bạn cần xác thực quản trị viên để tiếp tục.",
  "Admin role required.": "Tài khoản hiện tại không có quyền quản trị.",
  "Barcode must contain 8 to 14 digits.": "Mã vạch phải gồm từ 8 đến 14 chữ số.",
  "Barcode is empty.": "Vui lòng nhập hoặc quét mã sản phẩm.",
  "The code was decoded, but it does not contain a supported retail GTIN.": "Đã đọc được mã, nhưng mã này không chứa GTIN bán lẻ để tra cứu sản phẩm.",
  "GTIN must contain 8, 12, 13, or 14 digits.": "GTIN phải có độ dài 8, 12, 13 hoặc 14 chữ số.",
  "UPC-E must contain exactly 8 digits.": "Mã UPC-E phải có đúng 8 chữ số.",
  "UPC-E number system must be 0 or 1.": "Mã UPC-E sử dụng number system chưa được hỗ trợ.",
  "Product not found.": "Không tìm thấy sản phẩm với mã vạch này.",
  "Label image must be JPEG, PNG, or WebP.": "Ảnh nhãn phải có định dạng JPEG, PNG hoặc WebP.",
  "Label image must not exceed 8 MB.": "Ảnh nhãn không được lớn hơn 8 MB.",
  "The uploaded file is not a valid image.": "Tệp đã chọn không phải ảnh hợp lệ.",
  "No readable text was found in the label image.": "Không tìm thấy chữ đủ rõ trong ảnh nhãn.",
  "Label image quality is too low.": "Ảnh nhãn quá mờ, tối hoặc có độ phân giải thấp. Vui lòng chụp lại gần hơn.",
  "OCR engine is not installed on the server.": "Dịch vụ đọc nhãn chưa sẵn sàng trên máy chủ.",
  "Pantry item not found.": "Không tìm thấy sản phẩm trong tủ đồ.",
  "Favorite not found.": "Sản phẩm không còn trong danh sách yêu thích.",
  "Meal plan not found.": "Không tìm thấy kế hoạch bữa ăn.",
};

const STATUS_MESSAGES: Record<number, string> = {
  400: "Yêu cầu chưa hợp lệ. Vui lòng kiểm tra lại thông tin.",
  401: "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.",
  403: "Bạn không có quyền thực hiện thao tác này.",
  404: "Không tìm thấy dữ liệu được yêu cầu.",
  409: "Dữ liệu đã tồn tại hoặc vừa được thay đổi. Vui lòng kiểm tra lại.",
  422: "Một số thông tin chưa hợp lệ. Vui lòng kiểm tra các trường đã nhập.",
  429: "Bạn thao tác quá nhanh. Vui lòng đợi một lát rồi thử lại.",
  500: "Hệ thống đang gặp sự cố. Vui lòng thử lại sau.",
  502: "Nguồn dữ liệu bên ngoài đang tạm thời gián đoạn. Vui lòng thử lại sau.",
  503: "Dịch vụ đang khởi động hoặc tạm thời chưa sẵn sàng. Vui lòng thử lại sau ít phút.",
};

const FIELD_LABELS: Record<string, string> = {
  email: "email",
  password: "mật khẩu",
  display_name: "tên hiển thị",
  barcode: "mã vạch",
  age: "tuổi",
  height_cm: "chiều cao",
  weight_kg: "cân nặng",
  biological_sex: "giới tính sinh học",
  activity_level: "mức vận động",
  target_weight_loss_kg_week: "mục tiêu giảm cân",
};

function validationMessage(detail: unknown): string | null {
  if (!Array.isArray(detail) || detail.length === 0) return null;
  const first = detail[0];
  if (!first || typeof first !== "object") return null;
  const row = first as { loc?: unknown; type?: unknown };
  const loc = Array.isArray(row.loc) ? row.loc : [];
  const fieldKey = String(loc.at(-1) ?? "thông tin");
  const field = FIELD_LABELS[fieldKey] ?? fieldKey.replaceAll("_", " ");
  const type = String(row.type ?? "");
  if (type.includes("missing")) return `Vui lòng nhập ${field}.`;
  if (type.includes("email")) return "Email chưa đúng định dạng.";
  if (type.includes("string_too_short")) return `${field} chưa đủ độ dài yêu cầu.`;
  if (type.includes("less_than") || type.includes("greater_than")) return `${field} nằm ngoài phạm vi cho phép.`;
  return `Giá trị ${field} chưa hợp lệ.`;
}

function parseApiFailure(payload: unknown, status: number): { message: string; code: string } {
  const root = payload && typeof payload === "object" ? payload as Record<string, unknown> : null;
  const detail = root && "detail" in root ? root.detail : payload;
  if (detail && typeof detail === "object" && !Array.isArray(detail)) {
    const structured = detail as Record<string, unknown>;
    const message = typeof structured.message === "string" ? structured.message : null;
    const code = typeof structured.code === "string" ? structured.code : "API_ERROR";
    if (message) return { message: DETAIL_MESSAGES[message] ?? message, code };
  }
  const validation = validationMessage(detail);
  if (validation) return { message: validation, code: "VALIDATION_ERROR" };
  if (typeof detail === "string" && DETAIL_MESSAGES[detail]) {
    return { message: DETAIL_MESSAGES[detail], code: "API_ERROR" };
  }
  return {
    message: STATUS_MESSAGES[status] ?? (status >= 500 ? STATUS_MESSAGES[500] : "Không thể hoàn tất yêu cầu. Vui lòng thử lại."),
    code: status >= 500 ? "SERVER_ERROR" : "API_ERROR",
  };
}

export function toUserMessage(error: unknown, fallback = "Không thể hoàn tất thao tác. Vui lòng thử lại."): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof DOMException && error.name === "NotAllowedError") {
    return "Bạn chưa cấp quyền truy cập camera. Hãy cho phép camera trong cài đặt trình duyệt.";
  }
  if (error instanceof TypeError) return "Không thể kết nối đến máy chủ. Vui lòng kiểm tra mạng và thử lại.";
  return fallback;
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
    let payload: unknown = null;
    if (contentType.includes("application/json")) {
      try { payload = await response.json(); } catch { payload = null; }
    }
    const failure = parseApiFailure(payload, response.status);
    throw new ApiError(failure.message, response.status, failure.code, response.headers.get("x-request-id"));
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const defaultProfile: UserProfile = {
  goal: "general",
  allergies: [],
  disliked_ingredients: []
};
