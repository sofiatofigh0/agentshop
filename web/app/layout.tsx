import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Job Opportunity Agent",
  description:
    "An agent that evaluates whether a role is worth pursuing, selectively researches missing information, and turns a candidate's experience into a tailored application package.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
