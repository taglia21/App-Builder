import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FreelancePro",
  description: "FreelancePro is an all-in-one project management tool designed for freelancers. It allows users to manage projects, track deadlines, and organize client work. Key features: - Project Dashboard: See all active projects at a glance. - Status Tracking: Monitor project state (Active, Completed, On Hold). - Client Organization: Keep project details in one place.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
