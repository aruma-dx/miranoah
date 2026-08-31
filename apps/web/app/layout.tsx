import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MIRANOAH",
  description: "すべてを見渡し、一つも取りこぼさない。",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ja">
      <body>{children}</body>
    </html>
  );
}
