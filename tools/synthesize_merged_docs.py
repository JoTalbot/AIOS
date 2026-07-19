#!/usr/bin/env python3
"""Synthesize 'merged best' docs for topics that have variants.

For each variant that is a genuine alternate version of a canon in the same layer
(same source basename stem), take the canon as base and append any `##` sections
present in the variant but missing from the canon. Non-destructive: writes
`<layer>/<canon>.merged.md` and a MERGED_INDEX.md.

Constitution variants are different books/articles (complementary), NOT alternate
versions, so they are skipped (kept as separate docs).
"""
import os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AIOS = os.path.join(ROOT, "docs", "aios")

SKIP_LAYERS = {"constitution"}  # variants there are different books, not alternates

H2 = re.compile(r"^##\s+(.+?)\s*$", re.M)


def headings(text):
    return [h.strip().lower() for h in H2.findall(text)]


def main():
    produced = []
    for layer in sorted(os.listdir(AIOS)):
        ldir = os.path.join(AIOS, layer)
        vdir = os.path.join(ldir, "variants")
        if not os.path.isdir(vdir) or layer in SKIP_LAYERS:
            continue
        for vf in sorted(os.listdir(vdir)):
            if not vf.endswith(".md"):
                continue
            # strip slice prefix: sliceN__<origbasename>
            m = re.match(r"^slice[0-9]_[a-z0-9_]+?__(.+)$", vf)
            if not m:
                continue
            orig = m.group(1)
            canon_path = os.path.join(ldir, orig)
            if not os.path.isfile(canon_path):
                continue  # canon elsewhere or different name
            with open(canon_path, encoding="utf-8", errors="ignore") as f:
                canon = f.read()
            with open(os.path.join(vdir, vf), encoding="utf-8", errors="ignore") as f:
                variant = f.read()
            canon_norm = re.sub(r"\s+", " ", canon.lower())
            vsections = re.split(r"(?m)^(##\s+.+)$", variant)
            added = []  # list of (kind, text)
            # 1) whole ## sections from variant absent in canon
            canon_h = set(headings(canon))
            i = 1
            while i + 1 < len(vsections):
                head, body = vsections[i], vsections[i + 1]
                i += 2
                if head[2:].strip().lower() in canon_h:
                    continue
                body_norm = re.sub(r"\s+", " ", body.lower()).strip()
                if body_norm and body_norm not in canon_norm:
                    added.append(("section", head + "\n" + body.strip()))
            # 2) if variant has no ## sections merged, pull unique meaningful bullet/lines
            if not any("section" == k for k, _ in added):
                for line in variant.splitlines():
                    s = line.strip()
                    if not s:
                        continue
                    if not (s.startswith("-") or s.startswith("*") or re.match(r"^\d+\.", s)):
                        # allow definition-ish lines too (label: text)
                        if ":" not in s and len(s.split()) < 3:
                            continue
                    s_norm = re.sub(r"\s+", " ", s.lower())
                    if len(s_norm) < 6:
                        continue
                    if s_norm not in canon_norm:
                        added.append(("line", s))
            if not added:
                continue
            body_added = "\n\n".join(
                a.strip() if k == "section" else "- " + a.strip().lstrip("-* ")
                for k, a in added
            )
            merged = canon.rstrip() + "\n\n---\n\n## Merged from variant\n\n" + body_added + "\n"
            out = canon_path[:-3] + ".merged.md"
            with open(out, "w", encoding="utf-8") as f:
                f.write(merged)
            produced.append((layer, orig, vf, len(added)))

    # MERGED_INDEX.md
    lines = ["# AIOS — Синтезированные документы (merged best)", ""]
    lines.append("Для тем, имеющих альтернативные версии (variants/), сгенерирован единый "
                 "«merged best» документ: канон взят за основу, из вариантов добавлены "
                 "отсутствующие в каноне разделы (`##`). Файлы: `<layer>/<canon>.merged.md`.")
    lines.append("")
    lines.append("Конституция (`constitution/`) исключена: её варианты — это разные книги/статьи "
                 "(дополняющие, а не альтернативные), поэтому оставлены как отдельные документы.")
    lines.append("")
    lines.append("| Слой | Канон | Добавлено из варианта | Разделов добавлено |")
    lines.append("|---|---|---|---|")
    for layer, orig, vf, n in produced:
        lines.append(f"| {layer} | {orig} | {vf} | {n} |")
    with open(os.path.join(AIOS, "MERGED_INDEX.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"generated {len(produced)} merged docs; MERGED_INDEX.md written")


if __name__ == "__main__":
    main()
