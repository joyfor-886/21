import type { Metadata } from "next"
import { Noto_Serif_SC } from "next/font/google"
import "./globals.css"

const notoSerif = Noto_Serif_SC({
  variable: "--font-noto-serif",
  subsets: ["latin"],
  weight: ["200", "300", "400", "700", "900"],
  display: "swap",
})

export const metadata: Metadata = {
  title: "枢墨 Ssuma",
  description: "东方美学 AI 规划意识空间",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html
      lang="zh-CN"
      data-theme="xuanmo"
      className={`${notoSerif.variable} antialiased`}
    >
      <body>{children}</body>
    </html>
  )
}
