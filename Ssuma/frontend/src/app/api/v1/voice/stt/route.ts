import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const audio = formData.get("audio") as File | null;

    if (!audio) {
      return NextResponse.json({ detail: "No audio file" }, { status: 400 });
    }

    const backendForm = new FormData();
    backendForm.append("audio", audio, audio.name);

    const language = request.nextUrl.searchParams.get("language") || "zh";
    const url = `${BACKEND}/api/v1/voice/stt?language=${encodeURIComponent(language)}`;

    const resp = await fetch(url, {
      method: "POST",
      body: backendForm,
    });

    const data = await resp.json();
    return NextResponse.json(data, { status: resp.status });
  } catch (e: any) {
    console.error("[STT Proxy] Error:", e.message);
    return NextResponse.json({ detail: e.message }, { status: 500 });
  }
}
