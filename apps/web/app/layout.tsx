import type { Metadata } from "next";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: "MAWSIM — demand-aware promo planning",
  description:
    "Forecast Dubai retail demand from events, weather and holidays; plan promotions against it; measure the lift.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  );
}
