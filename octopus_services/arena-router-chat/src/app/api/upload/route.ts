import { NextResponse } from "next/server";
import { writeFile } from "node:fs/promises";
import { existsSync, mkdirSync } from "node:fs";
import path from "node:path";
import { randomUUID } from "node:crypto";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const ALLOWED_MIME = new Set([
  "image/png", "image/jpeg", "image/webp", "image/gif",
  "application/pdf",
]);
const MAX_SIZE = 20 * 1024 * 1024;

const UPLOAD_DIR = path.join(process.cwd(), "public", "uploads");
if (!existsSync(UPLOAD_DIR)) mkdirSync(UPLOAD_DIR, { recursive: true });

export async function POST(req: Request) {
  try {
    const form = await req.formData();
    const files = form.getAll("file").filter((v): v is File => v instanceof File);
    if (!files.length) {
      return NextResponse.json({ error: "no files" }, { status: 400 });
    }
    const saved: Array<{
      id: string; name: string; size: number; mime: string;
      url: string; kind: "image" | "pdf" | "file";
    }> = [];
    for (const f of files) {
      if (f.size > MAX_SIZE) {
        return NextResponse.json(
          { error: `file too large: ${f.name} (${f.size} > ${MAX_SIZE})` },
          { status: 413 },
        );
      }
      if (!ALLOWED_MIME.has(f.type)) {
        return NextResponse.json(
          { error: `unsupported type ${f.type} for ${f.name}. Allowed: PNG/JPG/WebP/GIF/PDF.` },
          { status: 415 },
        );
      }
      const id = randomUUID();
      const ext = guessExt(f.name, f.type);
      const safe = `${id}${ext}`;
      const dest = path.join(UPLOAD_DIR, safe);
      const buf = Buffer.from(await f.arrayBuffer());
      await writeFile(dest, buf);
      const url = `/chat/uploads/${safe}`;
      const kind =
        f.type.startsWith("image/") ? "image"
        : f.type === "application/pdf" ? "pdf"
        : "file";
      saved.push({ id, name: f.name, size: f.size, mime: f.type, url, kind });
    }
    return NextResponse.json({ ok: true, files: saved });
  } catch (e: any) {
    return NextResponse.json({ error: e?.message ?? String(e) }, { status: 500 });
  }
}

function guessExt(name: string, mime: string): string {
  const m = /\.([a-zA-Z0-9]{1,8})$/.exec(name);
  if (m) return "." + m[1].toLowerCase();
  if (mime === "image/png") return ".png";
  if (mime === "image/jpeg") return ".jpg";
  if (mime === "image/webp") return ".webp";
  if (mime === "image/gif") return ".gif";
  if (mime === "application/pdf") return ".pdf";
  return ".bin";
}
