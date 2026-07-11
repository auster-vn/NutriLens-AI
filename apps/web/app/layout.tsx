import type { Metadata, Viewport } from "next";
import { AppShell } from "@/components/AppShell";
import { AuthProvider } from "@/components/AuthProvider";
import "./globals.css";

export const metadata: Metadata = {
  title: "NutriLens AI",
  description: "Barcode nutrition intelligence and grounded nutrition assistant",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    title: "NutriLens AI",
    statusBarStyle: "default"
  }
};

export const viewport: Viewport = {
  themeColor: "#13795b"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <body>
        <AuthProvider><AppShell>{children}</AppShell></AuthProvider>
      </body>
    </html>
  );
}
