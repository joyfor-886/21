import type { Metadata } from 'next'
import '../consciousness/styles/consciousness.css'

export const metadata: Metadata = {
  title: '枢墨 Ssuma — 意识空间',
  description: '东方美学 AI 规划意识空间',
}

export default function ConsciousnessLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return children
}
