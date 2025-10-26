import type React from "react";
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Analytics } from "@vercel/analytics/next";
import "./globals.css";

const _geist = Geist({ subsets: ["latin"] });
const _geistMono = Geist_Mono({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "CanvAI",
  description:
    "CanvAI is a learning assistant that helps you learn faster and smarter.",
  generator: "CanvAI",
  keywords: [
    "CanvAI",
    "Canvas Learning Assistant",
    "Learning Assistant",
    "Learning",
    "Assistant",
    "AI",
    "AI Assistant",
    "AI Learning Assistant",
    "AI Learning",
    "AI Assistant",
    "AI Learning Assistant",
  ],
  authors: [{ name: "CanvAI", url: "https://canvai.com" }],
  creator: "CanvAI",
  publisher: "CanvAI",
  openGraph: {
    title: "CanvAI - Canvas Learning Assistant",
    description:
      "CanvAI is a learning assistant that helps you learn faster and smarter.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`font-sans antialiased`}>
        {children}
        <Analytics />
      </body>
    </html>
  );
}
