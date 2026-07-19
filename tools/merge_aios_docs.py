#!/usr/bin/env python3
"""Merge the four AIOS documentation slices into one layered tree under docs/aios/.

Policy (best-of-each):
- Each (layer, topic_key) group gets exactly ONE canonical doc = the most complete
  (largest non-trivial body). Tie-break: slice4 (2026 archive, living) > slice3 (v6)
  > slice2 (v2.1.1 exec) > slice1 (native repo).
- Other members of the group become variants/<slice>__<name>.
- Exact byte-duplicate bodies are kept only once.
- Slice 4 (docs/aios_archive_2026) is flagged as the actively-developed source.
"""
import os, re, hashlib, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SLICES = {
    "slice1_native": os.path.join(ROOT, "docs"),
    "slice1_constitution": os.path.join(ROOT, "constitution"),
    "slice2_exec_v2_1_1": os.path.join(ROOT, "docs", "executable_layer"),
    "slice3_v6": os.path.join(ROOT, "docs", "aios_v6"),
    "slice4_archive_2026": os.path.join(ROOT, "docs", "aios_archive_2026"),
}
LIVING = "slice4_archive_2026"
SLICE_RANK = {"slice4_archive_2026": 4, "slice3_v6": 3, "slice2_exec_v2_1_1": 2,
              "slice1_constitution": 1, "slice1_native": 1}

# Map a source path -> (layer, slice)
def classify(path, slice_name):
    rel = os.path.relpath(path, SLICES[slice_name])
    parts = rel.split(os.sep)
    name = parts[-1]
    if slice_name == "slice4_archive_2026":
        layer = parts[0] if parts[0] != "root" else "meta"
        return layer, slice_name
    if slice_name == "slice2_exec_v2_1_1":
        return "exec_layer", slice_name
    if slice_name == "slice1_constitution":
        return "constitution", slice_name
    if slice_name == "slice3_v6":
        # aios_v6/{docs,memory,plans,qa}/name
        layer = parts[0] if len(parts) > 1 else "meta"
        return layer, slice_name
    # slice1 native: docs/<subdir>/name  (skip already-merged slices)
    if len(parts) == 1:
        # top-level docs/*.md -> meta layer
        return "meta", slice_name
    sub = parts[0]
    if sub in ("executable_layer", "aios_v6", "aios_archive_2026"):
        return None, slice_name
    return sub, slice_name

VERSUFFIX = re.compile(r"[_-]?v?\d+([._]\d+)*(_v\d+)?|v\d+-v\d+|_\d+(_v\d+)?$", re.I)
PREFIX = re.compile(r"^(aios[_\-]?|book[_\-]?|article[_\-]?)", re.I)

def topic_key(name):
    n = name[:-3] if name.lower().endswith(".md") else name
    n = PREFIX.sub("", n)
    n = VERSUFFIX.sub("", n)
    n = re.sub(r"[^a-z0-9]+", "_", n.lower()).strip("_")
    return n or "untitled"

def body_size(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return len(f.read().strip())
    except Exception:
        return 0

def collect():
    out = os.path.join(ROOT, "docs", "aios")
    groups = {}  # (layer, key) -> list of (path, slice, size, hash, body)
    for sname, sdir in SLICES.items():
        if not os.path.isdir(sdir):
            continue
        for dp, _, files in os.walk(sdir):
            ap = os.path.abspath(dp)
            if ap == os.path.abspath(out) or ap.startswith(os.path.abspath(out) + os.sep):
                continue  # never read our own output tree
            for fn in files:
                if not fn.lower().endswith(".md"):
                    continue
                fp = os.path.join(dp, fn)
                layer, sn = classify(fp, sname)
                if layer is None:
                    continue
                with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                    body = f.read().strip()
                h = hashlib.md5(body.encode("utf-8", "ignore")).hexdigest()
                key = topic_key(fn)
                groups.setdefault((layer, key), []).append(
                    {"path": fp, "slice": sn, "size": len(body), "hash": h, "name": fn, "layer": layer}
                )
    return groups

def main():
    groups = collect()
    out = os.path.join(ROOT, "docs", "aios")
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out, exist_ok=True)
    totals = {"canon": 0, "variant": 0, "dropped_dup": 0}
    index = {}

    # Re-group purely by topic key (layer only affects placement of the canonical).
    by_key = {}
    for (layer, key), items in groups.items():
        by_key.setdefault(key, []).extend(items)

    # Canonical layer priority when a topic spans layers: pick the layer of the
    # richest version; tie -> preferred layer vocabulary.
    LAYER_PRIORITY = ["constitution","core","autonomy","intelligence","memory","memory_advanced",
        "knowledge","communication","compute","federation","federation_advanced","governance",
        "governance_advanced","identity_trust","security","security_advanced","execution","deployment",
        "monitoring","observability_advanced","storage","testing","qa","plans","roadmaps","meta",
        "agents","applications","architecture","orchestration","planning","mcp","model","skills",
        "foundation","reviews","docs","exec_layer"]

    for key, items in sorted(by_key.items()):
        # unique by hash
        seen = {}
        for it in items:
            if it["hash"] in seen:
                totals["dropped_dup"] += 1
                continue
            seen[it["hash"]] = it
        uniq = list(seen.values())
        # canon: richest body, tie -> highest slice rank
        canon = sorted(uniq, key=lambda x: (x["size"], SLICE_RANK[x["slice"]]), reverse=True)[0]
        # target layer: prefer the layer owning the canonical; else highest-priority layer present
        present = {it["layer"] for it in uniq}
        target = canon["layer"]
        if target not in LAYER_PRIORITY:
            target = sorted(present, key=lambda l: LAYER_PRIORITY.index(l) if l in LAYER_PRIORITY else 999)[0]
        ldir = os.path.join(out, target)
        vdir = os.path.join(ldir, "variants")
        os.makedirs(ldir, exist_ok=True)
        cname = canon["name"]
        dst = os.path.join(ldir, cname)
        if os.path.exists(dst):
            cname = f"canon__{cname}"
            dst = os.path.join(ldir, cname)
        shutil.copy2(canon["path"], dst)
        totals["canon"] += 1
        variants = [x for x in uniq if x["hash"] != canon["hash"]]
        for v in variants:
            os.makedirs(vdir, exist_ok=True)
            vn = f"{v['slice']}__{v['name']}"
            shutil.copy2(v["path"], os.path.join(vdir, vn))
            totals["variant"] += 1
        index.setdefault(target, []).append(
            (key, cname, canon["slice"], canon["size"], [ (x["slice"], x["name"], x["layer"]) for x in variants ])
        )
    # write INDEX.md
    lines = ["# AIOS — Объединённая документация (best-of-each)", ""]
    lines.append("Единое дерево, собранное из 4 срезов проекта AIOS. Для каждой темы выбран "
                 "**канонический** документ (самый полный), альтернативные версии — в `variants/`.")
    lines.append("")
    lines.append("## Срезы (источники)")
    lines.append("- `slice1_native` — исходный каркас репозитория (`docs/core`, `docs/memory`, `docs/constitution` и т.д.)")
    lines.append("- `slice1_constitution` — папка `constitution/` репозитория (книги/статьи конституции v2.1.1)")
    lines.append("- `slice2_exec_v2_1_1` — манифесты исполняемого слоя v2.1.1 (`docs/executable_layer`)")
    lines.append("- `slice3_v6` — спецификация v6 / v6.1 Global Federation (`docs/aios_v6`, из `AIOS.zip`)")
    lines.append("- `slice4_archive_2026` — **активно развивающийся** архитектурный архив 2026 (`docs/aios_archive_2026`, из `AIOS_Archive_2026.zip`). Дополняется дальше — считать живым источником.")
    lines.append("")
    lines.append(f"Итог: канонических документов = **{totals['canon']}**, вариантов = **{totals['variant']}**, "
                 f"удалено точных дублей = **{totals['dropped_dup']}**.")
    lines.append("")
    for layer in sorted(index):
        lines.append(f"## Слой: `{layer}`")
        lines.append("")
        lines.append("| Тема | Канон (источник, байт) | Варианты |")
        lines.append("|---|---|---|")
        for key, cname, cslice, csize, vs in sorted(index[layer]):
            vtxt = ", ".join(f"{s}::{n}@{l}" for s, n, l in vs) or "—"
            lines.append(f"| {key} | {cname} (`{cslice}`, {csize}) | {vtxt} |")
        lines.append("")
    with open(os.path.join(out, "INDEX.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("canon=%d variant=%d dropped_dup=%d layers=%d" % (
        totals["canon"], totals["variant"], totals["dropped_dup"], len(index)))

if __name__ == "__main__":
    main()
