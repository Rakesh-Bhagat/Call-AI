import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Voice Assistant",
  description: "Talk to the Gemini Live voice agent",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
