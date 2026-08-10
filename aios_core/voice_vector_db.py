#!/usr/bin/env python3
"""
AIOS Vector Voice Fingerprint Database & Neural Matcher
Сохраняет векторные профили голосов всех контактов в векторную базу данных
для высокоточной классификации спикеров на шумных фоновых диктофонных записях.
"""

import os
import sys
import json
import math
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

VECTOR_DB_FILE = REPO_ROOT / "data" / "voice_vector_chroma_db.json"
logger = logging.getLogger("aios.voice_vector")


class VoiceVectorDB:
    """Векторная база профилей голоса для сравнения косинусного сходства (Cosine Similarity)."""

    def __init__(self):
        self.db_path = VECTOR_DB_FILE
        self.vectors: Dict[str, Dict[str, Any]] = self._load_db()

    def _load_db(self) -> Dict[str, Dict[str, Any]]:
        if self.db_path.exists():
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(self.vectors, f, indent=2, ensure_ascii=False)

    def register_voice_vector(self, contact_id: str, name: str, vector: List[float], role: str = "Google Контакт"):
        """Регистрирует или обновляет усредненный вектор голоса для контакта."""
        if not vector or len(vector) == 0:
            return

        norm = math.sqrt(sum(x*x for x in vector) + 1e-9)
        norm_vector = [x / norm for x in vector]

        if contact_id in self.vectors:
            # Усреднение с предыдущим вектором
            old_vec = self.vectors[contact_id]["vector"]
            dim = len(norm_vector)
            avg_vec = [(old_vec[i] + norm_vector[i]) / 2.0 for i in range(min(dim, len(old_vec)))]
            avg_norm = math.sqrt(sum(x*x for x in avg_vec) + 1e-9)
            norm_vector = [x / avg_norm for x in avg_vec]

        self.vectors[contact_id] = {
            "contact_id": contact_id,
            "name": name,
            "role": role,
            "vector": norm_vector,
            "vector_dim": len(norm_vector)
        }
        self._save_db()
        logger.info(f"✅ Зарегистрирован вектор голоса: {name} (ID: {contact_id})")

    def match_speaker(self, input_vector: List[float], threshold: float = 0.60) -> Tuple[str, str, float]:
        """
        Ищет наиболее близкого спикера по косинусному сходству.
        Возвращает (contact_id, name, score).
        """
        if not input_vector or not self.vectors:
            return ("spk_owner", "Я (Владелец)", 0.5)

        norm = math.sqrt(sum(x*x for x in input_vector) + 1e-9)
        norm_input = [x / norm for x in input_vector]

        best_id = "spk_owner"
        best_name = "Я (Владелец)"
        best_score = -1.0

        for cid, data in self.vectors.items():
            ref_vec = data["vector"]
            if len(ref_vec) != len(norm_input):
                continue
            dot = sum(a * b for a, b in zip(norm_input, ref_vec))
            if dot > best_score:
                best_score = dot
                best_id = cid
                best_name = data["name"]

        if best_score < threshold:
            return ("spk_unknown", "Фоновый Голос", round(float(best_score), 3))

        return (best_id, best_name, round(float(best_score), 3))


if __name__ == "__main__":
    vdb = VoiceVectorDB()
    vdb.register_voice_vector("c_owner", "Я (Владелец)", [0.1]*12, role="Владелец")
    vdb.register_voice_vector("c_yarik", "[PRIVATE_CONTACT]", [0.5]*12, role="Дизайнер")
    matched = vdb.match_speaker([0.48]*12)
    print("Matched:", matched)
