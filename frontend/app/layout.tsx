import type { Metadata } from "next";
import "./globals.css";
import TopNav from "@/components/TopNav";
import Disclaimer from "@/components/Disclaimer";
import { THEME_BOOT_SCRIPT } from "@/lib/theme";

export const metadata: Metadata = {
  title: "QuantLab",
  description: "Build your own investment strategy, test it on past data, and try it with paper money.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_BOOT_SCRIPT }} />
      </head>
      <body className="min-h-full">
        <TopNav />
        <div className="mx-auto w-full max-w-[1320px] px-4 pb-10 pt-5 md:px-6">
          <main>{children}</main>
          <Disclaimer />
        </div>
      </body>
    </html>
  );
}
