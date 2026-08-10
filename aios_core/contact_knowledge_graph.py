#!/usr/bin/env python3
"""
AIOS Contact Relationship Knowledge Graph & AI Dossier Generator
Строит граф связей между контактами, упоминаний людей и объектов,
и генерирует накопительное ИИ-Досье на каждого контакта Google.
"""

import os
import sys
import re
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aios_core.calls_crm_engine import get_all_dialogues, get_contacts_with_dialogues

GRAPH_CACHE_FILE = REPO_ROOT / "data" / "contact_knowledge_graph_cache.json"
DOSSIER_CACHE_FILE = REPO_ROOT / "data" / "contact_dossiers_cache.json"

logger = logging.getLogger("aios.knowledge_graph")


def build_relationship_knowledge_graph() -> Dict[str, Any]:
    """Строит социальный граф связей, упоминаний контактов и проектов."""
    contacts = get_contacts_with_dialogues()
    dialogues = get_all_dialogues()

    nodes = []
    edges = []
    edges_set = set()

    # 1. Нода Владельца
    nodes.append({
        "id": "node_owner",
        "label": "Я (Владелец)",
        "group": "owner",
        "shape": "diamond",
        "color": "#3B82F6",
        "size": 25,
        "details": "Главный профиль владельца AIOS"
    })

    # 2. Ноды контактов
    contact_names = []
    for c in contacts:
        c_id = f"node_{c['contact_id']}"
        c_name = c["name"]
        contact_names.append(c_name)

        nodes.append({
            "id": c_id,
            "label": f"{c_name} ({c['dialogues_count']})",
            "group": "contact",
            "color": "#10B981" if c["dialogues_count"] > 1 else "#00F0FF",
            "size": 15 + min(20, c["dialogues_count"] * 3),
            "details": f"{c['phone']} | {c['role']}"
        })

        # Связь с владельцем
        edge_key = f"node_owner->{c_id}"
        if edge_key not in edges_set:
            edges.append({
                "from": "node_owner",
                "to": c_id,
                "label": f"{c['dialogues_count']} диалогов",
                "value": c["dialogues_count"],
                "color": "#334155"
            })
            edges_set.add(edge_key)

    # 3. Перекрестные связи и упоминания между контактами
    for d in dialogues:
        summary_text = d.get("summary", "")
        transcription_text = d.get("transcription", "")
        full_text = (summary_text + " " + transcription_text).lower()

        c_info = d.get("google_contact", {})
        c1_id = f"node_{c_info.get('id') or c_info.get('name')}"

        for other_c in contacts:
            other_name = other_c["name"]
            c2_id = f"node_{other_c['contact_id']}"

            if c1_id != c2_id and other_name.lower() in full_text and len(other_name) > 3:
                edge_key = f"{c1_id}->{c2_id}"
                if edge_key not in edges_set:
                    edges.append({
                        "from": c1_id,
                        "to": c2_id,
                        "label": "упоминание в разговоре",
                        "value": 2,
                        "color": "#00F0FF",
                        "dashes": True
                    })
                    edges_set.add(edge_key)

    graph_data = {
        "nodes": nodes,
        "edges": edges,
        "total_nodes": len(nodes),
        "total_edges": len(edges)
    }

    GRAPH_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(GRAPH_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(graph_data, f, indent=2, ensure_ascii=False)

    return graph_data


def generate_contact_ai_dossier(contact_id: str) -> Dict[str, Any]:
    """Формирует накопительное ИИ-досье и психопортрет контакта."""
    contacts = get_contacts_with_dialogues()
    matched_contact = None
    for c in contacts:
        if str(c["contact_id"]) == str(contact_id) or c["name"] == str(contact_id):
            matched_contact = c
            break

    if not matched_contact:
        return {"status": "error", "reason": "Контакт не найден"}

    # Собираем контекст разговоров
    dialogues = matched_contact.get("dialogues", [])
    summaries = [d.get("summary_preview", "") for d in dialogues if d.get("summary_preview")]
    combined_summaries = "\n---\n".join(summaries[:5])

    prompt = f"""
Составь накопительное ИИ-Досье и психопортрет для Google Контакта:
Имя: {matched_contact['name']}
Телефон: {matched_contact['phone']}
Роль/Сфера: {matched_contact['role']}
Всего разговоров: {matched_contact['dialogues_count']}

История выжимок прошлых звонков:
\"\"\"
{combined_summaries}
\"\"\"

Формат ответа:
👤 **Психологический портрет и стиль общения**: (характер, манера речи, скорость принятия решений)
💡 **Ключевые интересы и предмет сотрудничества**: (что заказывает, какие вопросы обсуждает)
💰 **Согласованные финансовые условия**: (скидки, цены, договоренности)
🔗 **Упоминаемые связи и проекты**: (партнеры, сотрудники, авто, задачи)
🎯 **Рекомендации по дальнейшей коммуникации**: (как эффективно вести диалог)
"""
    try:
        from aios_core.llm_balancer import LLMBalancer
        balancer = LLMBalancer()
        dossier_text = balancer.chat(
            messages=[{"role": "user", "content": prompt}],
            system="Ты — аналитик отдела разведки контактов и CRM операционной системы AIOS."
        )
    except Exception as e:
        logger.warning(f"Ошибка LLM генератора досье: {e}")
        dossier_text = f"👤 **Профиль {matched_contact['name']}**:\nВсего диалогов: {matched_contact['dialogues_count']} шт."

    dossier = {
        "contact_id": matched_contact["contact_id"],
        "name": matched_contact["name"],
        "phone": matched_contact["phone"],
        "role": matched_contact["role"],
        "dialogues_count": matched_contact["dialogues_count"],
        "dossier_text": dossier_text,
        "dialogues": dialogues
    }

    return dossier


if __name__ == "__main__":
    graph = build_relationship_knowledge_graph()
    print(f"Граф связей построен: {graph['total_nodes']} нод, {graph['total_edges']} ребер")
