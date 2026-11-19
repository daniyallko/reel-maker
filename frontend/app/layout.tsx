import type { Metadata, Viewport } from "next";
import { Anton_SC, Space_Mono } from "next/font/google";
import "./globals.css";
import "./glyph-fonts.css";
import "./glyph.css";

const spaceMono = Space_Mono({
  subsets: ["latin"],
  weight: ["400", "700"],
  style: ["normal", "italic"],
  variable: "--font-space-mono",
  display: "swap",
});
const anton = Anton_SC({ subsets: ["latin"], weight: "400", variable: "--font-anton-sc", display: "swap" });

export const metadata: Metadata = {
  title: "glyph animals — LINK2REEL",
  description: "Turn any public URL into a sourced vertical motion video.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#000000",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" data-theme="dark" className={`${spaceMono.variable} ${anton.variable}`}>
      <body style={{ fontFamily: '"Space Mono", monospace' }}>{children}</body>
    </html>
  );
}
