import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Legal Clinic Leads",
  description: "Lead intake for the legal clinic.",
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
