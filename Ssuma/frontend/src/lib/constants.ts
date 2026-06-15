export const API_BASE = ""

export const PHASE_LABELS: Record<string, { label: string; icon: string; desc: string }> = {
  qishu: { label: "启枢", icon: "chat", desc: "追问澄清" },
  tanyin: { label: "探隐", icon: "file", desc: "探求隐情" },
  caiheng: { label: "裁衡", icon: "filter", desc: "价值审视" },
  zhenwei: { label: "甄微", icon: "search", desc: "技术评审" },
  ceshu: { label: "策书", icon: "file", desc: "任务规划" },
  powang: { label: "破妄", icon: "filter", desc: "覆盖验证" },
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

export const COMPLEXITY_LABELS: Record<string, { label: string; color: string }> = {
  simple: { label: "简单", color: "#22c55e" },
  moderate: { label: "中等", color: "#eab308" },
  complex: { label: "复杂", color: "#f97316" },
  platform: { label: "平台级", color: "#ef4444" },
}

export const AUTOPILOT_PHASE_LABELS: Record<string, string> = {
  qishu: "启枢 · 追问澄清",
  caiheng: "裁衡 · 价值审视",
  zhenwei: "甄微 · 技术评审",
  ceshu: "策书 · 任务规划",
  ningmo: "凝墨 · 方案整合",
  powang: "破妄 · 覆盖验证",
  jianyan: "渐衍 · 分阶段生成",
}