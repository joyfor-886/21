import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = request.nextUrl;
    const text = searchParams.get("text");
    const voice = searchParams.get("voice") || "xiaoxiao";

    if (!text) {
      return NextResponse.json({ detail: "Text is required" }, { status: 400 });
    }

    // Forward all params, properly encoding + signs
    const params = new URLSearchParams();
    params.set("text", text);
    params.set("voice", voice);
    const rate = searchParams.get("rate");
    const volume = searchParams.get("volume");
    if (rate) params.set("rate", rate);
    if (volume) params.set("volume", volume);

    const url = `${BACKEND}/api/v1/voice/tts?${params.toString()}`;

    const resp = await fetch(url);

    if (!resp.ok) {
      const errText = await resp.text();
      return NextResponse.json({ detail: errText }, { status: resp.status });
    }

    const audioBuffer = await resp.arrayBuffer();

    return new NextResponse(audioBuffer, {
      status: 200,
      headers: {
        "Content-Type": "audio/mpeg",
        "Content-Disposition": "inline; filename=tts.mp3",
        "Cache-Control": "no-cache",
      },
    });
  } catch (e: any) {
    console.error("[TTS Proxy] Error:", e.message);
    return NextResponse.json({ detail: e.message }, { status: 500 });
  }
}
