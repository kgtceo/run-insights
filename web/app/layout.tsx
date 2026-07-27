import type { Metadata } from "next";
import "./globals.css";

const url = "https://run-insights.kareemghazal.com";
const title = "run-insights — objective facts + grounded feedback from a run's splits";
const description =
  "Enter a run's per-km splits and get the split, pace fade, HR decoupling and effort type — computed deterministically — plus a short coaching note grounded in exactly those numbers. Illustrative demo — not coaching or medical advice.";

export const metadata: Metadata = {
  metadataBase: new URL(url),
  title,
  description,
  alternates: { canonical: "/" },
  openGraph: {
    type: "website",
    url,
    siteName: "run-insights",
    title,
    description,
    locale: "en_GB",
    images: [{ url: "/og.jpg", width: 1200, height: 630, alt: "run-insights — AI running-activity analyzer" }],
  },
  twitter: { card: "summary_large_image", title, description, images: ["/og.jpg"] },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
