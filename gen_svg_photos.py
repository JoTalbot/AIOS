#!/usr/bin/env python3
"""Уникальные SVG-иллюстрации для позиций склада.
Каждая картинка уникальна: иконка детали + цвет категории + подпись."""
import json
import re
from pathlib import Path

ROOT = Path("/root/AIOS")
INV = ROOT / "data" / "inventory.json"
OUT = ROOT / "data" / "photos" / "unique"
OUT.mkdir(parents=True, exist_ok=True)

# иконки (простые и выразительные SVG-векторы) по типу детали
def icon_for(name: str) -> str:
    n = name.lower()
    if "полуос" in n:
        return '<line x1="70" y1="90" x2="250" y2="90" stroke="#374151" stroke-width="12"/><circle cx="70" cy="90" r="28" fill="none" stroke="#374151" stroke-width="8"/><circle cx="70" cy="90" r="14" fill="#374151"/><rect x="235" y="80" width="20" height="20" rx="3" fill="#374151"/>'
    if "пружин" in n:
        return '<path d="M160 30 c-30 0 -30 15 0 15 c30 0 30 15 0 15 c-30 0 -30 15 0 15 c30 0 30 15 0 15 c-30 0 -30 15 0 15 c30 0 30 15 0 15" fill="none" stroke="#374151" stroke-width="10" stroke-linecap="round"/>'
    if "амортизатор" in n or "стойк" in n:
        return '<circle cx="160" cy="35" r="12" fill="none" stroke="#374151" stroke-width="8"/><line x1="160" y1="47" x2="160" y2="75" stroke="#374151" stroke-width="10"/><rect x="140" y="75" width="40" height="60" rx="6" fill="#374151"/><circle cx="160" cy="145" r="12" fill="none" stroke="#374151" stroke-width="8"/>'
    if "маховик" in n:
        return '<circle cx="160" cy="90" r="50" fill="none" stroke="#374151" stroke-width="14" stroke-dasharray="8 4"/><circle cx="160" cy="90" r="24" fill="none" stroke="#374151" stroke-width="8"/><circle cx="160" cy="90" r="10" fill="#374151"/>'
    if "корзина" in n:
        return '<circle cx="160" cy="90" r="50" fill="none" stroke="#374151" stroke-width="12"/><circle cx="160" cy="90" r="28" fill="none" stroke="#374151" stroke-width="6"/><line x1="160" y1="45" x2="160" y2="62" stroke="#374151" stroke-width="6"/><line x1="160" y1="118" x2="160" y2="135" stroke="#374151" stroke-width="6"/><line x1="115" y1="90" x2="132" y2="90" stroke="#374151" stroke-width="6"/><line x1="188" y1="90" x2="205" y2="90" stroke="#374151" stroke-width="6"/>'
    if "диск сцеплен" in n or "ведомый диск" in n:
        return '<circle cx="160" cy="90" r="50" fill="none" stroke="#374151" stroke-width="14"/><circle cx="160" cy="90" r="18" fill="#374151"/><rect x="135" y="70" width="12" height="12" rx="2" fill="#9ca3af"/><rect x="173" y="70" width="12" height="12" rx="2" fill="#9ca3af"/><rect x="135" y="98" width="12" height="12" rx="2" fill="#9ca3af"/><rect x="173" y="98" width="12" height="12" rx="2" fill="#9ca3af"/>'
    if "карбюратор" in n:
        return '<rect x="125" y="60" width="70" height="60" rx="8" fill="#374151"/><circle cx="145" cy="45" r="12" fill="none" stroke="#374151" stroke-width="8"/><circle cx="175" cy="45" r="12" fill="none" stroke="#374151" stroke-width="8"/><line x1="115" y1="110" x2="135" y2="110" stroke="#374151" stroke-width="8"/><rect x="130" y="115" width="60" height="12" rx="2" fill="#6b7280"/>'
    if "бензонасос" in n:
        return '<circle cx="160" cy="85" r="28" fill="#374151"/><rect x="150" y="110" width="20" height="25" fill="#374151"/><path d="M140 135l40 10" stroke="#374151" stroke-width="8" fill="none"/><path d="M135 75h-20v-15" stroke="#374151" stroke-width="8" fill="none"/><path d="M185 75h20v-15" stroke="#374151" stroke-width="8" fill="none"/>'
    if "помпа" in n or "насос охлажден" in n:
        return '<circle cx="160" cy="85" r="32" fill="none" stroke="#374151" stroke-width="10"/><circle cx="160" cy="85" r="16" fill="#374151"/><path d="M130 95l-30 25h40z" fill="#374151"/><circle cx="200" cy="65" r="10" fill="none" stroke="#374151" stroke-width="6"/>'
    if "термостат" in n:
        return '<rect x="130" y="65" width="60" height="50" rx="10" fill="#374151"/><path d="M160 35v30M160 115v30" stroke="#374151" stroke-width="12"/><line x1="140" y1="90" x2="180" y2="90" stroke="#fff" stroke-width="6"/>'
    if "хомут" in n:
        return '<circle cx="160" cy="90" r="46" fill="none" stroke="#374151" stroke-width="10"/>'
    if "тройник" in n or "штуцер" in n:
        return '<path d="M160 30v50M160 80l-45 55M160 80l45 55" stroke="#374151" stroke-width="12" fill="none"/>'
    if "реле" in n:
        return '<rect x="110" y="45" width="100" height="70" rx="8" fill="#374151"/><path d="M135 62l25 36 20-22" stroke="#fff" stroke-width="8" fill="none"/><line x1="130" y1="130" x2="190" y2="130" stroke="#374151" stroke-width="10"/>'
    if "стеклоподъемник" in n:
        return '<path d="M90 70h140M110 40l50 55 50-55" stroke="#374151" stroke-width="10" fill="none"/>'
    if "ручка" in n:
        return '<path d="M110 80q50-40 100 0q-50 40-100 0z" stroke="#374151" stroke-width="10" fill="none"/>'
    if "замок" in n:
        return '<circle cx="160" cy="70" r="34" stroke="#374151" stroke-width="10" fill="none"/><rect x="135" y="80" width="50" height="45" rx="6" fill="#374151"/>'
    if "тяга" in n:
        return '<line x1="80" y1="90" x2="240" y2="90" stroke="#374151" stroke-width="10"/><circle cx="80" cy="90" r="16" fill="#374151"/><circle cx="240" cy="90" r="16" fill="#374151"/>'
    if "пистон" in n or "клипс" in n:
        return '<circle cx="160" cy="90" r="34" fill="#374151"/><path d="M150 120v30M170 120v30" stroke="#374151" stroke-width="10"/>'
    if "колпак" in n:
        return '<circle cx="160" cy="95" r="55" fill="none" stroke="#374151" stroke-width="10"/><circle cx="160" cy="95" r="20" fill="#374151"/><path d="M120 60l-25-30M200 60l25-30" stroke="#374151" stroke-width="8"/>'
    if "метиз" in n or "болт" in n or "гайк" in n:
        return '<circle cx="140" cy="80" r="18" fill="#374151"/><line x1="140" y1="98" x2="140" y2="140" stroke="#374151" stroke-width="12"/><rect x="115" y="130" width="50" height="10" fill="#6b7280"/><circle cx="205" cy="95" r="14" fill="#374151"/><line x1="205" y1="109" x2="205" y2="130" stroke="#374151" stroke-width="9"/>'
    if "патрубок" in n:
        return '<path d="M80 100q40-55 80 0t80 0" stroke="#111827" stroke-width="16" fill="none"/>'
    if "горловин" in n:
        return '<circle cx="160" cy="80" r="36" fill="#374151"/><circle cx="160" cy="80" r="16" fill="#fff"/>'
    # дефолт: шестерёнка
    return '<circle cx="160" cy="90" r="34" fill="none" stroke="#374151" stroke-width="12"/><circle cx="160" cy="90" r="10" fill="#374151"/>'

COLORS = {
    "подвеска": "#1d4ed8", "трансмиссия": "#7c3aed", "двигатель": "#b91c1c",
    "система_охлаждения": "#0e7490", "тормозная_система": "#a16207",
    "электрооборудование": "#0369a1", "оптика": "#c2410c", "кузов": "#4d7c0f",
    "колеса": "#4338ca", "прочее": "#52525b",
}


def slug(name: str) -> str:
    n = re.sub(r"[^a-zа-я0-9]+", "-", name.lower()).strip("-")[:40]
    return n or "item"


def render(name: str, category: str, idx: int) -> str:
    color = COLORS.get(category, "#52525b")
    icon = icon_for(name)
    label = name[:60]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="320" height="180" viewBox="0 0 320 180">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#f3f4f6"/>
      <stop offset="1" stop-color="#e5e7eb"/>
    </linearGradient>
  </defs>
  <rect width="320" height="180" fill="url(#bg)"/>
  <rect width="320" height="6" fill="{color}"/>
  <g transform="translate(0,-10)">{icon}</g>
  <text x="160" y="162" text-anchor="middle" font-family="Arial, sans-serif" font-size="13" font-weight="600" fill="#111827">{label}</text>
  <text x="160" y="176" text-anchor="middle" font-family="monospace" font-size="9" fill="#6b7280">AIOS-{idx:03d} · {category}</text>
</svg>"""


def main(target_indices: list[int] = None) -> None:
    items = json.loads(INV.read_text(encoding="utf-8"))
    made = 0
    for idx, it in enumerate(items, 1):
        if target_indices and idx not in target_indices:
            continue
        name = it.get("name", "")
        dest = OUT / f"ws_u_{idx:03d}.svg"
        dest.write_text(render(name, it.get("category", ""), idx), encoding="utf-8")
        it["photos"] = [str(dest)]
        it["photo"] = str(dest)
        made += 1
        print(f"  [+] Сгенерирован SVG ({idx:02d}): {name}")
    INV.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nВсего сгенерировано и обновлено в инвентаре: {made} SVG-изображений.")


if __name__ == "__main__":
    import sys
    # 10 целевых позиций из списка товаров с фото из интернета:
    # 8: Полуоси заднего моста
    # 11: Пружины подвески
    # 12: Амортизаторы / стойки
    # 13: Маховик двигателя
    # 14: Корзина сцепления
    # 15: Ведомый диск сцепления
    # 20: Карбюраторы (Солекс / Озон)
    # 21: Бензонасос механический
    # 26: Помпа водяная (насос охлаждения)
    # 27: Термостат в корпусе
    targets = [8, 11, 12, 13, 14, 15, 20, 21, 26, 27]
    main(targets)
