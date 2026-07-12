import type { Metadata, Viewport } from "next";
import { AppShell } from "@/components/AppShell";
import { AuthProvider } from "@/components/AuthProvider";
import "./globals.css";

export const metadata: Metadata = {
  title: "NutriLens AI – Thông tin dinh dưỡng thông minh",
  description: "Quét mã vạch thực phẩm, phân tích dinh dưỡng và hỏi trợ lý AI về sức khoẻ",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    title: "NutriLens AI",
    statusBarStyle: "default",
  },
};

export const viewport: Viewport = {
  themeColor: "#10b981",
  viewportFit: "cover",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <head>
      </head>
      <body>
        <AuthProvider>
          <AppShell>{children}</AppShell>
        </AuthProvider>
      </body>
    </html>
  );
}
