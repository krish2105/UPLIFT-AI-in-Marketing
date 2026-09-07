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
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wdth,wght@12..96,75..100,200..800&family=Instrument+Sans:wght@400..700&family=Martian+Mono:wght@200..700&family=Marcellus&family=Karla:wght@300..700&family=DM+Mono:wght@300;400;500&family=Archivo:wdth,wght@62..125,100..900&family=Figtree:wght@300..900&family=Geist+Mono:wght@200..700&family=Noto+Kufi+Arabic:wght@300..700&family=Noto+Naskh+Arabic:wght@400..700&family=Noto+Sans+Arabic:wght@300..700&family=Noto+Sans+Devanagari:wght@300..700&display=swap" />
      </head>
      <body>{children}</body>
    </html>
  );
}
