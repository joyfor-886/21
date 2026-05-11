export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000"

export const PHASE_LABELS: Record<string, { label: string; icon: string; desc: string }> = {
  qishu: { label: "启枢", icon: "chat", desc: "头脑风暴" },
  questionnaire: { label: "问卷", icon: "file", desc: "需求收集" },
  caiheng: { label: "裁衡", icon: "filter", desc: "CEO审视" },
  zhenwei: { label: "甄微", icon: "search", desc: "技术评审" },
  ceshu: { label: "策书", icon: "file", desc: "实施计划" },
  powang: { label: "破妄", icon: "filter", desc: "需求覆盖" },
  jianyan: { label: "渐衍", icon: "leaf", desc: "分阶段生成" },
  ningmo: { label: "凝墨", icon: "file", desc: "方案生成" },
  completed: { label: "完成", icon: "check-circle", desc: "规划完成" },
  intent_detection: { label: "检测", icon: "thunderbolt", desc: "意图检测" },
}

export const CHANNEL_LABELS: Record<string, { label: string; theme: "primary" | "warning" | "default" }> = {
  fast: { label: "快速通道", theme: "primary" },
  standard: { label: "标准通道", theme: "default" },
  deep: { label: "深度通道", theme: "warning" },
}

export const CLASSICAL_QUOTES = [
  { text: "致虚极，守静笃", source: "《道德经》第十六章" },
  { text: "上善若水，水善利万物而不争", source: "《道德经》第八章" },
  { text: "知人者智，自知者明", source: "《道德经》第三十三章" },
  { text: "信言不美，美言不信", source: "《道德经》第八十一章" },
  { text: "为学日益，为道日损", source: "《道德经》第四十八章" },
  { text: "知足者富，强行者有志", source: "《道德经》第三十三章" },
  { text: "三人行，必有我师", source: "《论语》" },
  { text: "学而不思则罔，思而不学则殆", source: "《论语》" },
]

export const TIER_THEME_MAP: Record<string, "primary" | "warning" | "danger"> = {
  adequate: "primary",
  basic: "warning",
  insufficient: "danger",
}
