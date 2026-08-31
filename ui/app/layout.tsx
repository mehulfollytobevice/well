import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "WellGround",
  description: "Grounded geothermal ops Q&A for Utah FORGE",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
