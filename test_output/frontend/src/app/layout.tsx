import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TestDash",
  description: "A test dashboard app",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
