import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI-PoweredCrmAutomation",
  description: "AI-Powered Crm Automation",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
