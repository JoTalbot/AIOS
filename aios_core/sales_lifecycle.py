"""Жизненный цикл продажи запчасти: ТТН → отправка → доставка/возврат.

Модуль является единым источником состояния для бизнес-логики продажи:

* после создания ТТН товар резервируется на складе и создаётся задача отправки;
* после подтверждения отправки резерв списывается с физического склада;
* при доставке сделка закрывается и (если известна сумма) фиксируется в финансах;
* при возврате товар не возвращается на склад автоматически — создаётся задача
  принять его физически, чтобы не появились «виртуальные» остатки.

Хранение намеренно простое и совместимо с существующим проектом: JSON-файлы в
``data/``. Все переходы идемпотентны: повторное событие ТТН/доставки не создаёт
дубликат резерва или финансовой записи.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

PROJECT_ROOT = Path(__file__).resolve().parents[1]

WAITING_SHIPMENT = {"awaiting_shipment", "ttn_created", "sent"}
TRACKING_ACTIVE = {"awaiting_shipment", "in_transit", "returning"}
FINAL_STATUSES = {"delivered", "returned", "return_received", "cancelled"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _stamp(value: datetime | None = None) -> str:
    return (value or _now()).isoformat(timespec="seconds")


def _parse_stamp(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _ttn(value: Any) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _amount(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        if isinstance(value, str):
            clean = value.replace(" ", "").replace("\u00a0", "").replace(",", ".")
            match = re.search(r"\d+(?:\.\d+)?", clean)
            if not match:
                return None
            value = match.group(0)
        result = float(value)
        return result if result > 0 else None
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any, default: int) -> int:
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return default


def _generic_reference(value: str) -> bool:
    return value.strip().casefold() in {
        "", "этот товар", "этот", "эту", "этой", "товар", "посылку", "посылка",
        "эту посылку", "его", "ее", "її", "його", "цей товар", "цю посилку",
        "посилку", "товар цей",
    }


class SalesLifecycle:
    """Хранилище и переходы состояний продаж.

    ``root`` существует прежде всего для тестов; в рабочем процессе это
    ``/root/AIOS``. Методы не отправляют сообщения сами — они возвращают
    готовые факты/тексты, а Telegram-слой доставляет их пользователю.
    """

    def __init__(self, root: Path | str | None = None):
        self.root = Path(root) if root is not None else PROJECT_ROOT
        self.data_dir = self.root / "data"
        self.sales_file = self.data_dir / "sales_lifecycle.json"
        self.tasks_file = self.data_dir / "sales_tasks.json"
        self.pending_file = self.data_dir / "pending_sales.json"
        self.inventory_file = self.data_dir / "inventory.json"
        self.finance_file = self.data_dir / "finance.json"
        self.lock_file = self.data_dir / ".sales_lifecycle.lock"

    # ---- low-level persistence -------------------------------------------------
    @contextmanager
    def _lock(self) -> Iterator[None]:
        """Сериализовать переходы между ботом и таймером трекинга."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        lock = self.lock_file.open("a+", encoding="utf-8")
        try:
            try:
                import fcntl
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            except Exception:
                # Windows здесь не используется, но бизнес-логика не должна
                # ломаться из-за отсутствия flock в тестовом окружении.
                pass
            yield
        finally:
            try:
                import fcntl
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
            lock.close()

    @staticmethod
    def _load(path: Path, default: Any) -> Any:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, type(default)) else default
        except Exception:
            return default

    @staticmethod
    def _save(path: Path, value: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, path)

    def _sales(self) -> list[dict]:
        return self._load(self.sales_file, [])

    def _tasks(self) -> list[dict]:
        return self._load(self.tasks_file, [])

    # ---- search / legacy synchronization --------------------------------------
    @staticmethod
    def _sale_matches(sale: dict, reference: str) -> bool:
        ref = (reference or "").strip()
        if not ref or _generic_reference(ref):
            return True
        number = _ttn(ref)
        if number and number == _ttn(sale.get("ttn")):
            return True
        ref_l = ref.casefold()
        item = str(sale.get("item") or "").casefold()
        return bool(item and (item == ref_l or ref_l in item or item in ref_l))

    def _find_one(self, sales: list[dict], reference: str, statuses: set[str] | None = None) -> dict:
        candidates = [
            sale for sale in sales
            if (statuses is None or sale.get("status") in statuses)
            and self._sale_matches(sale, reference)
        ]
        if not candidates:
            return {"status": "not_found"}
        # Сначала точное попадание в ТТН/название, затем наиболее свежая запись.
        ref = (reference or "").strip()
        if ref and not _generic_reference(ref):
            number = _ttn(ref)
            exact = [s for s in candidates if number and _ttn(s.get("ttn")) == number]
            if not exact:
                exact = [s for s in candidates if str(s.get("item") or "").casefold() == ref.casefold()]
            if len(exact) == 1:
                return {"status": "ok", "sale": exact[0]}
            if len(exact) > 1:
                candidates = exact
        if len(candidates) == 1:
            return {"status": "ok", "sale": candidates[0]}
        return {
            "status": "ambiguous",
            "sales": sorted(candidates, key=lambda s: str(s.get("updated_at") or s.get("created_at") or ""),
                            reverse=True),
        }

    def _find_pending(self, item: str, recipient: str, phone: str, ttn: str) -> dict | None:
        pending = self._load(self.pending_file, [])
        item_l = (item or "").strip().casefold()
        recipient_l = (recipient or "").strip().casefold()
        phone_digits = _ttn(phone)
        candidates: list[dict] = []
        for rec in pending:
            rec_ttn = _ttn(rec.get("ttn"))
            if ttn and rec_ttn == ttn:
                return rec
            if rec_ttn and rec_ttn != ttn:
                continue
            if rec.get("status") not in ("pending", "sent", "ttn_created", "awaiting_shipment"):
                continue
            rec_item = str(rec.get("item") or "").strip().casefold()
            if item_l and rec_item and not (item_l == rec_item or item_l in rec_item or rec_item in item_l):
                continue
            if recipient_l:
                rec_recipient = str(rec.get("recipient") or "").strip().casefold()
                if rec_recipient and rec_recipient != recipient_l:
                    continue
            if phone_digits:
                rec_phone = _ttn(rec.get("customer_phone"))
                if rec_phone and rec_phone != phone_digits:
                    continue
            candidates.append(rec)
        return candidates[-1] if candidates else None

    @staticmethod
    def _legacy_status(status: str) -> str:
        return {
            "awaiting_shipment": "ttn_created",
            "in_transit": "in_transit",
            "returning": "returning",
            "delivered": "closed",
            "returned": "returned",
            "return_received": "returned",
        }.get(status, status)

    def _sync_pending(self, sale: dict) -> None:
        """Поддержать старый pending_sales.json для существующего OLX-контура."""
        pending = self._load(self.pending_file, [])
        target: dict | None = None
        sale_ttn = _ttn(sale.get("ttn"))
        for rec in pending:
            if rec.get("sale_id") == sale.get("id") or (sale_ttn and _ttn(rec.get("ttn")) == sale_ttn):
                target = rec
                break
        if target is None:
            item_l = str(sale.get("item") or "").casefold()
            for rec in reversed(pending):
                if (rec.get("status") in ("pending", "sent", "ttn_created", "awaiting_shipment")
                        and str(rec.get("item") or "").casefold() == item_l):
                    target = rec
                    break
        if target is None:
            target = {
                "ts": sale.get("created_at") or _stamp(),
                "platform": sale.get("platform") or "manual",
                "chat": sale.get("chat") or "",
                "item": sale.get("item") or "",
                "amount": sale.get("amount"),
                "delivery": sale.get("delivery") or "",
                "customer_phone": sale.get("customer_phone") or "",
                "recipient": sale.get("recipient") or "",
            }
            pending.append(target)
        target.update({
            "sale_id": sale.get("id"),
            "ttn": sale.get("ttn") or "",
            "status": self._legacy_status(str(sale.get("status") or "")),
            "lifecycle_status": sale.get("status"),
            "updated_at": sale.get("updated_at") or _stamp(),
        })
        # pending_sales historically ограничен 50 записями.
        self._save(self.pending_file, pending[-50:])

    # ---- OLX publication ---------------------------------------------------------
    @staticmethod
    def _normalize_ad_title(value: Any) -> str:
        """Нормализация названий для безопасного сопоставления склад ↔ OLX."""
        text = str(value or "").casefold()
        text = re.sub(r"[^\wа-яіїєґ]+", " ", text, flags=re.IGNORECASE)
        return " ".join(text.split())

    def _inventory_available_for_sale(self, sale: dict) -> int | None:
        """Доступный остаток именно этой позиции или None, если её не нашли."""
        try:
            import run_inventory
            items = run_inventory._load(self.inventory_file)
            preferred = str((sale.get("inventory") or {}).get("item") or sale.get("item") or "")
            item = run_inventory._find(items, preferred)
            return run_inventory.available_qty(item) if item else None
        except Exception:
            return None

    def _find_olx_ad(self, sale: dict) -> tuple[dict | None, str]:
        """Найти единственное связанное объявление без рискованного угадывания."""
        try:
            journal = self._load(self.data_dir / "olx_published.json", [])
        except Exception:
            journal = []
        if not isinstance(journal, list):
            return None, "journal_unavailable"
        rows = [row for row in journal if isinstance(row, dict) and row.get("ad_id")]
        olx = sale.get("olx") if isinstance(sale.get("olx"), dict) else {}
        explicit_id = str(olx.get("ad_id") or sale.get("ad_id") or "")
        if explicit_id:
            match = next((row for row in rows if str(row.get("ad_id")) == explicit_id), None)
            return (match or {"ad_id": explicit_id, "title": ""}), "explicit"

        item = self._normalize_ad_title(sale.get("item"))
        if not item:
            return None, "empty_item"
        exact = [row for row in rows if self._normalize_ad_title(row.get("title")) == item]
        if len(exact) == 1:
            return exact[0], "exact_title"
        if len(exact) > 1:
            return None, "ambiguous_exact_title"

        # Частичное совпадение разрешаем только для достаточно конкретного
        # названия. «Фара» не должна снять несколько разных объявлений.
        if len(item) < 8:
            return None, "item_too_generic"
        partial = [
            row for row in rows
            if item in self._normalize_ad_title(row.get("title"))
        ]
        if len(partial) == 1:
            return partial[0], "title_contains_item"
        return None, "ambiguous_title" if partial else "not_found"

    def _mark_olx_journal_inactive(self, ad_id: str, now: datetime) -> None:
        """Не давать другим контурам считать снятое объявление активным."""
        journal_path = self.data_dir / "olx_published.json"
        journal = self._load(journal_path, [])
        if not isinstance(journal, list):
            return
        changed = False
        for row in journal:
            if isinstance(row, dict) and str(row.get("ad_id") or "") == str(ad_id):
                row.update({"active": False, "status": "deactivated", "deactivated_at": _stamp(now)})
                changed = True
        if changed:
            self._save(journal_path, journal)

    def _run_olx_deactivate(self, ad_id: str) -> dict:
        """Снять одно объявление с публикации через тот же adapter, что и бот."""
        py = "/opt/aios/.venv/bin/python"
        if not Path(py).exists():
            py = sys.executable
        command = [py, str(self.root / "run_account_control.py"), "olx", "delete", str(ad_id), "--confirm"]
        # OLX adapter может использовать системный Chrome через CDP, но xvfb
        # сохраняет совместимость с запуском без дисплея.
        if Path("/usr/bin/xvfb-run").exists():
            command = ["xvfb-run", "-a", "-s", "-screen 0 1440x900x24"] + command
        try:
            proc = subprocess.run(command, capture_output=True, text=True, timeout=190,
                                  cwd=str(self.root))
        except subprocess.TimeoutExpired:
            return {"status": "error", "error": "timeout при снятии объявления OLX"}
        except Exception as exc:
            return {"status": "error", "error": str(exc)[:200]}
        out = (proc.stdout or "").strip()
        try:
            start = out.find("{")
            data = json.loads(out[start:]) if start >= 0 else {}
        except Exception:
            data = {}
        status = str(data.get("status") or "")
        if status in ("deleted", "deactivated"):
            return {"status": "deactivated", "ad_id": str(ad_id), "adapter_status": status}
        return {
            "status": "error",
            "ad_id": str(ad_id),
            "error": str(data.get("error") or out[-300:] or proc.stderr or "OLX не вернул статус")[:300],
        }

    def _maybe_deactivate_olx(self, sale: dict, now: datetime, reason: str) -> dict:
        """Снять объявление, когда по позиции больше нет свободного остатка.

        Если товара осталось больше одной единицы, объявление намеренно остаётся
        активным: оно всё ещё соответствует доступному складу.
        """
        existing = sale.get("olx") if isinstance(sale.get("olx"), dict) else {}
        if existing.get("status") == "deactivated":
            return {**existing, "idempotent": True}

        available = self._inventory_available_for_sale(sale)
        if available is None:
            result = {"status": "skipped_inventory_unknown", "reason": reason,
                      "message": "Не удалось проверить остаток для снятия объявления OLX."}
        elif available > 0:
            result = {"status": "kept_active", "reason": reason, "available_qty": available,
                      "message": f"В остатке ещё {available} шт — объявление OLX оставлено активным."}
        else:
            ad, match_kind = self._find_olx_ad(sale)
            if ad is None:
                result = {
                    "status": "not_found" if match_kind == "not_found" else "ambiguous",
                    "reason": reason,
                    "match": match_kind,
                    "message": "Не найдено однозначное объявление OLX для автоматического снятия.",
                }
            else:
                result = self._run_olx_deactivate(str(ad.get("ad_id")))
                result.update({
                    "reason": reason,
                    "match": match_kind,
                    "title": str(ad.get("title") or ""),
                    "attempted_at": _stamp(now),
                })
                if result.get("status") == "deactivated":
                    self._mark_olx_journal_inactive(str(ad.get("ad_id")), now)
                    sale.setdefault("history", []).append({
                        "at": _stamp(now), "event": "olx_deactivated", "ad_id": str(ad.get("ad_id")),
                        "source": reason,
                    })
        # Не перезаписываем полезный id объявление при неудачном повторе.
        previous_id = existing.get("ad_id")
        sale["olx"] = {**existing, **result, "ad_id": result.get("ad_id") or previous_id or ""}
        return sale["olx"]

    def sync_active_olx_ads(self) -> dict:
        """Применить правило снятия публикаций к уже активным сделкам."""
        now = _now()
        with self._lock():
            sales = self._sales()
            outcomes = []
            for sale in sales:
                if sale.get("status") not in TRACKING_ACTIVE:
                    continue
                outcome = self._maybe_deactivate_olx(sale, now, "lifecycle_sync")
                outcomes.append({"sale_id": sale.get("id"), "status": outcome.get("status"),
                                 "ad_id": outcome.get("ad_id") or ""})
            self._save(self.sales_file, sales)
        return {"status": "ok", "outcomes": outcomes}

    def deactivate_olx_for_item(self, item: str, reason: str = "manual_sale") -> dict:
        """Снять объявление после продажи без ТТН, если остаток исчерпан."""
        now = _now()
        with self._lock():
            # В ручной продаже нет отдельной lifecycle-записи, поэтому строим
            # краткий контекст только для сопоставления склада и журнала OLX.
            synthetic_sale = {"item": str(item or ""), "inventory": {}, "history": []}
            return self._maybe_deactivate_olx(synthetic_sale, now, reason)

    # ---- tasks ------------------------------------------------------------------
    @staticmethod
    def _interval_minutes(kind: str) -> int:
        if kind == "return_receive":
            return _safe_int(os.environ.get("AIOS_RETURN_REMINDER_MINUTES"), 360)
        return _safe_int(os.environ.get("AIOS_SHIPMENT_REMINDER_MINUTES"), 120)

    def _ensure_task(self, tasks: list[dict], sale: dict, kind: str, now: datetime,
                     notify_now: bool = False) -> dict:
        task_id = f"{sale['id']}:{kind}"
        for task in tasks:
            if task.get("id") == task_id:
                if task.get("status") != "open" and kind == "return_receive":
                    task.update({"status": "open", "completed_at": "", "next_reminder_at": _stamp(now)})
                return task
        if kind == "ship":
            title = "Отправить товар по ТТН"
        else:
            title = "Принять возврат на склад"
        interval = self._interval_minutes(kind)
        task = {
            "id": task_id,
            "sale_id": sale["id"],
            "kind": kind,
            "title": title,
            "status": "open",
            "created_at": _stamp(now),
            "due_at": _stamp(now),
            "next_reminder_at": _stamp(now if notify_now else now + timedelta(minutes=interval)),
            "reminder_interval_minutes": interval,
            "reminder_count": 0,
        }
        tasks.append(task)
        return task

    @staticmethod
    def _complete_task(tasks: list[dict], sale_id: str, kind: str, now: datetime) -> None:
        for task in tasks:
            if task.get("sale_id") == sale_id and task.get("kind") == kind and task.get("status") == "open":
                task.update({"status": "done", "completed_at": _stamp(now), "next_reminder_at": ""})

    # ---- inventory / finance adapters ------------------------------------------
    def _reserve_inventory(self, sale: dict, now: datetime) -> dict:
        try:
            import run_inventory
            result = run_inventory.reserve(
                str(sale.get("item") or ""),
                qty=int(sale.get("qty") or 1),
                sale_id=str(sale.get("id") or ""),
                ttn=str(sale.get("ttn") or ""),
                data_path=self.inventory_file,
            )
        except Exception as exc:
            result = {"status": "error", "error": str(exc)[:200]}
        info = sale.setdefault("inventory", {})
        info.update({
            "reservation_attempted_at": _stamp(now),
            "reserved": result.get("status") == "ok",
            "item": (result.get("item") or {}).get("name") or sale.get("item") or "",
            "reservation_error": result.get("error") or "",
        })
        return result

    def _commit_inventory(self, sale: dict, now: datetime) -> dict:
        try:
            import run_inventory
            result = run_inventory.commit_reservation(
                sale_id=str(sale.get("id") or ""),
                name=str(sale.get("item") or ""),
                data_path=self.inventory_file,
            )
        except Exception as exc:
            result = {"status": "error", "error": str(exc)[:200]}
        info = sale.setdefault("inventory", {})
        info.update({
            "committed_at": _stamp(now),
            "committed": result.get("status") == "ok",
            "commit_error": result.get("error") or "",
        })
        return result

    def _record_finance(self, sale: dict) -> dict:
        if sale.get("finance_logged"):
            return {"status": "skipped", "reason": "already_logged"}
        amount = _amount(sale.get("amount"))
        if amount is None:
            return {"status": "skipped", "reason": "no_amount"}
        marker = f"sale:{sale.get('id')}"
        try:
            import run_finance
            for entry in run_finance._load(self.finance_file):
                if marker in str(entry.get("desc") or ""):
                    sale["finance_logged"] = True
                    return {"status": "ok", "entry": entry, "duplicate": True}
            desc = f"{sale.get('item') or 'товар'} · ТТН {sale.get('ttn') or '—'} · {marker}"
            result = run_finance.add("sale", amount, desc, data_path=self.finance_file)
            if result.get("status") == "ok":
                sale["finance_logged"] = True
            return result
        except Exception as exc:
            return {"status": "error", "error": str(exc)[:200]}

    # ---- primary state transitions ---------------------------------------------
    def register_ttn(self, *, ttn: str, item: str, amount: Any = None, recipient: str = "",
                     phone: str = "", city: str = "", warehouse: str = "", delivery: str = "",
                     platform: str = "", chat: str = "", source: str = "ttn", notify_now: bool = False) -> dict:
        """Зафиксировать созданную ТТН, резерв склада и задачу на отправку."""
        number = _ttn(ttn)
        if not number:
            return {"status": "error", "error": "Не указан номер ТТН"}
        item = str(item or "").strip()
        if not item:
            return {"status": "error", "error": "Не указан товар для ТТН"}
        now = _now()
        with self._lock():
            sales = self._sales()
            tasks = self._tasks()
            existing = next((sale for sale in sales if _ttn(sale.get("ttn")) == number), None)
            created = existing is None
            if existing is None:
                legacy = self._find_pending(item, recipient, phone, number)
                sale = {
                    "id": str((legacy or {}).get("sale_id") or f"sale-{uuid.uuid4().hex[:12]}"),
                    "created_at": str((legacy or {}).get("ts") or _stamp(now)),
                    "updated_at": _stamp(now),
                    "source": source,
                    "platform": str((legacy or {}).get("platform") or platform or ""),
                    "chat": str((legacy or {}).get("chat") or chat or ""),
                    "item": item,
                    "qty": 1,
                    "amount": _amount(amount) if _amount(amount) is not None else (legacy or {}).get("amount"),
                    "recipient": recipient or str((legacy or {}).get("recipient") or ""),
                    "customer_phone": phone or str((legacy or {}).get("customer_phone") or ""),
                    "city": city,
                    "warehouse": warehouse,
                    "delivery": delivery or str((legacy or {}).get("delivery") or ""),
                    "ttn": number,
                    "status": "awaiting_shipment",
                    "history": [{"at": _stamp(now), "event": "ttn_created", "source": source}],
                    "tracking": {},
                    "inventory": {},
                    "finance_logged": False,
                }
                sales.append(sale)
            else:
                sale = existing
                # Повтор ответа API/рестарт процесса не должен создавать новый товар.
                sale.update({
                    "updated_at": _stamp(now),
                    "item": sale.get("item") or item,
                    "amount": sale.get("amount") if sale.get("amount") is not None else _amount(amount),
                    "recipient": sale.get("recipient") or recipient,
                    "customer_phone": sale.get("customer_phone") or phone,
                    "city": sale.get("city") or city,
                    "warehouse": sale.get("warehouse") or warehouse,
                    "delivery": sale.get("delivery") or delivery,
                })
                if sale.get("status") in ("sent", "ttn_created"):
                    sale["status"] = "awaiting_shipment"

            if sale.get("status") in WAITING_SHIPMENT and not sale.get("inventory", {}).get("reserved"):
                inventory = self._reserve_inventory(sale, now)
            else:
                inventory = {"status": "ok" if sale.get("inventory", {}).get("reserved") else "skipped"}
            # При создании ТТН товар уже продан и зарезервирован. Если
            # свободного остатка не осталось, сразу снимаем связанное OLX-объявление.
            olx = self._maybe_deactivate_olx(sale, now, "ttn_created")
            # Повторный ответ API по уже доставленной/возвращённой ТТН не
            # должен воскресить закрытую задачу отправки.
            if sale.get("status") in WAITING_SHIPMENT:
                task = self._ensure_task(tasks, sale, "ship", now, notify_now=notify_now)
            else:
                task = next((t for t in tasks if t.get("sale_id") == sale.get("id") and t.get("kind") == "ship"), {})
            self._sync_pending(sale)
            self._save(self.sales_file, sales)
            self._save(self.tasks_file, tasks)
        return {
            "status": "ok",
            "created": created,
            "sale": sale,
            "task": task,
            "inventory": inventory,
            "olx": olx,
            "message": (
                f"ТТН {number} создана. Товар «{sale.get('item')}» зарезервирован: "
                "нужна отправка."
                if inventory.get("status") == "ok" else
                f"ТТН {number} создана, но резерв склада требует проверки: {inventory.get('error', 'нет совпадения')}"
            ),
        }

    def _commit_shipment(self, sale: dict, tasks: list[dict], now: datetime, source: str) -> dict:
        if sale.get("status") not in WAITING_SHIPMENT:
            return {"status": "skipped", "reason": sale.get("status")}
        inventory = self._commit_inventory(sale, now)
        # Fallback для старых/ручных ТТН: если объявление не было снято при
        # резервировании, повторяем проверку в момент фактической отправки.
        inventory["olx"] = self._maybe_deactivate_olx(sale, now, "shipped")
        sale.update({
            "status": "in_transit",
            "shipped_at": _stamp(now),
            "updated_at": _stamp(now),
        })
        sale.setdefault("history", []).append({"at": _stamp(now), "event": "shipped", "source": source})
        self._complete_task(tasks, str(sale.get("id")), "ship", now)
        return inventory

    @staticmethod
    def _not_found_message(action: str) -> str:
        verbs = {
            "shipped": "отправки",
            "delivered": "доставки",
            "returned": "возврата",
            "return_received": "приёма возврата",
        }
        return f"Не нашёл активную сделку для {verbs.get(action, 'операции')}. Укажите ТТН или название товара."

    @staticmethod
    def _ambiguous_message(action: str, sales: list[dict]) -> str:
        options = ", ".join(
            f"{s.get('item') or 'товар'} ({s.get('ttn') or 'без ТТН'})" for s in sales[:4]
        )
        return f"Нашёл несколько сделок: {options}. Укажите ТТН или точное название товара."

    def mark_shipped(self, reference: str = "", source: str = "owner") -> dict:
        """Зафиксировать факт передачи товара перевозчику."""
        now = _now()
        with self._lock():
            sales = self._sales()
            tasks = self._tasks()
            found = self._find_one(sales, reference, WAITING_SHIPMENT)
            if found.get("status") == "not_found":
                # Повторное сообщение владельца после перехода не должно выглядеть как ошибка.
                already = self._find_one(sales, reference, {"in_transit", "delivered", "returning", "returned"})
                if already.get("status") == "ok":
                    sale = already["sale"]
                    return {"status": "ok", "idempotent": True, "sale": sale,
                            "message": f"Товар «{sale.get('item')}» уже имеет статус «{sale.get('status')}»."}
                return {"status": "not_found", "message": self._not_found_message("shipped")}
            if found.get("status") == "ambiguous":
                return {"status": "ambiguous", "sales": found["sales"],
                        "message": self._ambiguous_message("shipped", found["sales"])}
            sale = found["sale"]
            inventory = self._commit_shipment(sale, tasks, now, source)
            self._sync_pending(sale)
            self._save(self.sales_file, sales)
            self._save(self.tasks_file, tasks)
        warning = "" if inventory.get("status") == "ok" else (
            f" Внимание: склад не удалось списать автоматически ({inventory.get('error', 'нужна проверка')}).")
        olx = inventory.get("olx") or sale.get("olx") or {}
        olx_note = " Объявление OLX снято с публикации." if olx.get("status") == "deactivated" else ""
        return {
            "status": "ok", "sale": sale, "inventory": inventory, "olx": olx,
            "message": (
                f"📦 Отправка подтверждена: «{sale.get('item')}» снят со склада и переведён в доставку."
                f" ТТН: {sale.get('ttn') or '—'}.{warning}{olx_note}"
            ),
        }

    def mark_delivered(self, reference: str = "", source: str = "owner") -> dict:
        """Закрыть сделку по доставленному товару и отразить продажу в финансах."""
        now = _now()
        with self._lock():
            sales = self._sales()
            tasks = self._tasks()
            found = self._find_one(sales, reference, WAITING_SHIPMENT | {"in_transit"})
            if found.get("status") == "not_found":
                already = self._find_one(sales, reference, {"delivered"})
                if already.get("status") == "ok":
                    sale = already["sale"]
                    return {"status": "ok", "idempotent": True, "sale": sale,
                            "message": f"Сделка по «{sale.get('item')}» уже закрыта как доставленная."}
                return {"status": "not_found", "message": self._not_found_message("delivered")}
            if found.get("status") == "ambiguous":
                return {"status": "ambiguous", "sales": found["sales"],
                        "message": self._ambiguous_message("delivered", found["sales"])}
            sale = found["sale"]
            inventory = {"status": "skipped"}
            if sale.get("status") in WAITING_SHIPMENT:
                inventory = self._commit_shipment(sale, tasks, now, source)
            sale.update({"status": "delivered", "delivered_at": _stamp(now), "updated_at": _stamp(now)})
            sale.setdefault("history", []).append({"at": _stamp(now), "event": "delivered", "source": source})
            self._complete_task(tasks, str(sale.get("id")), "ship", now)
            finance = self._record_finance(sale)
            self._sync_pending(sale)
            self._save(self.sales_file, sales)
            self._save(self.tasks_file, tasks)
        finance_note = ""
        if finance.get("status") == "ok":
            finance_note = " Продажа внесена в финансы."
        elif finance.get("status") == "error":
            finance_note = " Внимание: финансы не обновлены автоматически."
        return {
            "status": "ok", "sale": sale, "inventory": inventory,
            "olx": inventory.get("olx") or sale.get("olx") or {}, "finance": finance,
            "message": f"✅ Доставка подтверждена: сделка по «{sale.get('item')}» закрыта.{finance_note}",
        }

    def mark_returned(self, reference: str = "", source: str = "owner") -> dict:
        """Отметить возврат без автоматического добавления в остатки."""
        now = _now()
        with self._lock():
            sales = self._sales()
            tasks = self._tasks()
            found = self._find_one(sales, reference, WAITING_SHIPMENT | {"in_transit", "returning"})
            if found.get("status") == "not_found":
                already = self._find_one(sales, reference, {"returned", "return_received"})
                if already.get("status") == "ok":
                    sale = already["sale"]
                    return {"status": "ok", "idempotent": True, "sale": sale,
                            "message": f"Возврат по «{sale.get('item')}» уже зафиксирован."}
                return {"status": "not_found", "message": self._not_found_message("returned")}
            if found.get("status") == "ambiguous":
                return {"status": "ambiguous", "sales": found["sales"],
                        "message": self._ambiguous_message("returned", found["sales"])}
            sale = found["sale"]
            inventory = {"status": "skipped"}
            if sale.get("status") in WAITING_SHIPMENT:
                inventory = self._commit_shipment(sale, tasks, now, source)
            sale.update({"status": "returned", "returned_at": _stamp(now), "updated_at": _stamp(now)})
            sale.setdefault("history", []).append({"at": _stamp(now), "event": "returned", "source": source})
            self._complete_task(tasks, str(sale.get("id")), "ship", now)
            task = self._ensure_task(tasks, sale, "return_receive", now, notify_now=True)
            self._sync_pending(sale)
            self._save(self.sales_file, sales)
            self._save(self.tasks_file, tasks)
        return {
            "status": "ok", "sale": sale, "task": task, "inventory": inventory,
            "olx": inventory.get("olx") or sale.get("olx") or {},
            "message": (
                f"↩️ Возврат по «{sale.get('item')}» зафиксирован. Товар не добавлен в остатки автоматически: "
                "после фактического получения напишите «получил возврат <ТТН>»."
            ),
        }

    def mark_return_received(self, reference: str = "", source: str = "owner") -> dict:
        """Добавить физически полученный возврат обратно на склад."""
        now = _now()
        with self._lock():
            sales = self._sales()
            tasks = self._tasks()
            found = self._find_one(sales, reference, {"returned"})
            if found.get("status") == "not_found":
                already = self._find_one(sales, reference, {"return_received"})
                if already.get("status") == "ok":
                    sale = already["sale"]
                    return {"status": "ok", "idempotent": True, "sale": sale,
                            "message": f"Возврат «{sale.get('item')}» уже принят на склад."}
                return {"status": "not_found", "message": self._not_found_message("return_received")}
            if found.get("status") == "ambiguous":
                return {"status": "ambiguous", "sales": found["sales"],
                        "message": self._ambiguous_message("return_received", found["sales"])}
            sale = found["sale"]
            try:
                import run_inventory
                inventory = run_inventory.restore_return(
                    sale_id=str(sale.get("id") or ""),
                    name=str(sale.get("item") or ""),
                    qty=int(sale.get("qty") or 1),
                    price=float(sale.get("amount") or 0),
                    data_path=self.inventory_file,
                )
            except Exception as exc:
                inventory = {"status": "error", "error": str(exc)[:200]}
            if inventory.get("status") != "ok":
                return {"status": "error", "sale": sale, "inventory": inventory,
                        "message": f"Не удалось вернуть «{sale.get('item')}» в остатки: {inventory.get('error', '?')}"}
            sale.update({"status": "return_received", "return_received_at": _stamp(now), "updated_at": _stamp(now)})
            sale.setdefault("history", []).append({"at": _stamp(now), "event": "return_received", "source": source})
            sale.setdefault("inventory", {}).update({"returned_to_stock": True, "returned_to_stock_at": _stamp(now)})
            self._complete_task(tasks, str(sale.get("id")), "return_receive", now)
            self._sync_pending(sale)
            self._save(self.sales_file, sales)
            self._save(self.tasks_file, tasks)
        return {"status": "ok", "sale": sale, "inventory": inventory,
                "message": f"↩️ Возврат «{sale.get('item')}» принят и снова добавлен на склад."}

    # ---- tracking ---------------------------------------------------------------
    @staticmethod
    def classify_tracking_status(status: str) -> str:
        """Нормализовать человеческий статус Новой Почты без привязки к коду API."""
        low = " ".join(str(status or "").casefold().split())
        if not low:
            return "unknown"
        has_return = any(word in low for word in ("повернен", "повернут", "return to sender", "returned"))
        if has_return:
            if any(word in low for word in ("повертається", "повертается", "прямує до відправника",
                                             "едет к отправителю", "returning")):
                return "returning"
            return "returned"
        if any(word in low for word in (
            "отримано", "отриманий", "отримана", "получено", "получен", "получена",
            "видано", "видана", "вручено", "доставлено", "received", "delivered",
        )):
            return "delivered"
        if any(word in low for word in (
            "у відділенні", "у відділення", "в отделении", "прибуло у відділення",
            "прибыло в отделение", "arrived at the branch", "готове до видачі",
        )):
            return "at_branch"
        if any(word in low for word in (
            "відправлено", "отправлено", "у дорозі", "в дороге", "прямує", "принято",
            "прийнято", "in transit", "sent", "accepted",
        )):
            return "in_transit"
        if any(word in low for word in ("створено", "создано", "оформлено", "created", "оформлена")):
            return "created"
        return "other"

    def apply_tracking(self, ttn: str, tracking_status: str, details: dict | None = None) -> dict:
        """Сохранить результат трекинга и выполнить безопасные фактические переходы."""
        number = _ttn(ttn)
        now = _now()
        if not number:
            return {"status": "error", "error": "Некорректная ТТН", "notifications": []}
        phase = self.classify_tracking_status(tracking_status)
        with self._lock():
            sales = self._sales()
            tasks = self._tasks()
            sale = next((s for s in sales if _ttn(s.get("ttn")) == number), None)
            if sale is None:
                return {"status": "ignored", "reason": "unknown_ttn", "notifications": []}
            tracking = sale.setdefault("tracking", {})
            old_status = str(tracking.get("last_status") or "")
            changed = old_status != str(tracking_status or "")
            tracking.update({
                "last_status": str(tracking_status or ""),
                "last_phase": phase,
                "checked_at": _stamp(now),
            })
            # Не сохраняем ПД получателя/отправителя из details; для логики
            # достаточно нейтрального статуса Новой Почты.
            notifications: list[str] = []
            transition_result: dict | None = None
            if phase == "in_transit" and sale.get("status") in WAITING_SHIPMENT:
                inventory = self._commit_shipment(sale, tasks, now, "tracking")
                self._sync_pending(sale)
                transition_result = {"status": "shipped", "inventory": inventory}
                warning = "" if inventory.get("status") == "ok" else " Проверьте списание склада."
                notifications.append(
                    f"📦 ТТН {number}: перевозчик принял «{sale.get('item')}». Товар переведён в доставку.{warning}"
                )
                if (inventory.get("olx") or {}).get("status") == "deactivated":
                    notifications.append(f"🛒 ТТН {number}: связанное объявление OLX снято с публикации.")
            elif phase == "delivered" and sale.get("status") not in FINAL_STATUSES:
                inventory = {"status": "skipped"}
                if sale.get("status") in WAITING_SHIPMENT:
                    inventory = self._commit_shipment(sale, tasks, now, "tracking")
                sale.update({"status": "delivered", "delivered_at": _stamp(now), "updated_at": _stamp(now)})
                sale.setdefault("history", []).append({"at": _stamp(now), "event": "delivered", "source": "tracking"})
                self._complete_task(tasks, str(sale.get("id")), "ship", now)
                finance = self._record_finance(sale)
                self._sync_pending(sale)
                transition_result = {"status": "delivered", "inventory": inventory, "finance": finance}
                notifications.append(f"✅ ТТН {number}: «{sale.get('item')}» доставлен. Сделка закрыта.")
                if (inventory.get("olx") or {}).get("status") == "deactivated":
                    notifications.append(f"🛒 ТТН {number}: связанное объявление OLX снято с публикации.")
            elif phase == "returning" and sale.get("status") not in FINAL_STATUSES | {"returning"}:
                if sale.get("status") in WAITING_SHIPMENT:
                    self._commit_shipment(sale, tasks, now, "tracking")
                sale.update({"status": "returning", "updated_at": _stamp(now)})
                sale.setdefault("history", []).append({"at": _stamp(now), "event": "returning", "source": "tracking"})
                self._complete_task(tasks, str(sale.get("id")), "ship", now)
                self._sync_pending(sale)
                transition_result = {"status": "returning"}
                notifications.append(f"↩️ ТТН {number}: оформлен возврат «{sale.get('item')}» отправителю.")
            elif phase == "returned" and sale.get("status") not in {"returned", "return_received", "delivered"}:
                if sale.get("status") in WAITING_SHIPMENT:
                    self._commit_shipment(sale, tasks, now, "tracking")
                sale.update({"status": "returned", "returned_at": _stamp(now), "updated_at": _stamp(now)})
                sale.setdefault("history", []).append({"at": _stamp(now), "event": "returned", "source": "tracking"})
                self._complete_task(tasks, str(sale.get("id")), "ship", now)
                self._ensure_task(tasks, sale, "return_receive", now, notify_now=True)
                self._sync_pending(sale)
                transition_result = {"status": "returned"}
                notifications.append(
                    f"↩️ ТТН {number}: «{sale.get('item')}» возвращён. После фактического получения "
                    "напишите «получил возврат <ТТН>»."
                )
            elif changed:
                # Промежуточный статус также полезен, но только при изменении.
                notifications.append(f"📍 ТТН {number}: {str(tracking_status or 'статус не указан')[:500]}")
            sale["updated_at"] = _stamp(now)
            self._save(self.sales_file, sales)
            self._save(self.tasks_file, tasks)
        return {"status": "ok", "sale": sale, "phase": phase, "changed": changed,
                "transition": transition_result, "notifications": notifications}

    # ---- task views / reminders -------------------------------------------------
    def active_tracking_sales(self) -> list[dict]:
        """Продажи с ТТН, которые ещё нужно опрашивать у Новой Почты."""
        return [
            sale for sale in self._sales()
            if sale.get("status") in TRACKING_ACTIVE and _ttn(sale.get("ttn"))
        ]

    def list_open_tasks(self) -> list[dict]:
        sales = {str(s.get("id")): s for s in self._sales()}
        rows = []
        for task in self._tasks():
            if task.get("status") != "open":
                continue
            sale = sales.get(str(task.get("sale_id")))
            if sale is None:
                continue
            rows.append({"task": task, "sale": sale})
        return sorted(rows, key=lambda row: str(row["task"].get("due_at") or row["task"].get("created_at") or ""))

    def due_notifications(self, now: datetime | None = None) -> list[dict]:
        """Вернуть созревшие напоминания и перенести следующее без отправки Telegram."""
        now = now or _now()
        notifications: list[dict] = []
        with self._lock():
            sales = {str(s.get("id")): s for s in self._sales()}
            tasks = self._tasks()
            changed = False
            for task in tasks:
                if task.get("status") != "open":
                    continue
                sale = sales.get(str(task.get("sale_id")))
                if sale is None:
                    continue
                due_at = _parse_stamp(task.get("next_reminder_at"))
                if due_at is None or due_at > now:
                    continue
                kind = task.get("kind")
                if kind == "ship":
                    if sale.get("status") not in WAITING_SHIPMENT:
                        self._complete_task(tasks, str(sale.get("id")), "ship", now)
                        changed = True
                        continue
                    text = (
                        f"📦 Задача: отправьте «{sale.get('item')}» по ТТН {sale.get('ttn')}. "
                        f"После передачи в Новую Почту напишите: «отправил {sale.get('ttn')}»."
                    )
                elif kind == "return_receive":
                    if sale.get("status") != "returned":
                        self._complete_task(tasks, str(sale.get("id")), "return_receive", now)
                        changed = True
                        continue
                    text = (
                        f"↩️ Задача: примите возврат «{sale.get('item')}» по ТТН {sale.get('ttn')} "
                        f"и затем напишите: «получил возврат {sale.get('ttn')}»."
                    )
                else:
                    continue
                interval = _safe_int(task.get("reminder_interval_minutes"), self._interval_minutes(str(kind)))
                task["next_reminder_at"] = _stamp(now + timedelta(minutes=interval))
                task["reminder_count"] = int(task.get("reminder_count") or 0) + 1
                task["last_reminder_at"] = _stamp(now)
                changed = True
                notifications.append({"task": task, "sale": sale, "text": text})
            if changed:
                self._save(self.tasks_file, tasks)
        return notifications

    def migrate_legacy_pending_sales(self) -> dict:
        """Один раз перенести старые записи ``sent + ttn`` в новый цикл."""
        pending = self._load(self.pending_file, [])
        migrated = skipped = errors = 0
        for rec in pending:
            number = _ttn(rec.get("ttn"))
            if not number:
                skipped += 1
                continue
            if rec.get("status") not in ("sent", "ttn_created", "awaiting_shipment"):
                skipped += 1
                continue
            result = self.register_ttn(
                ttn=number,
                item=str(rec.get("item") or ""),
                amount=rec.get("amount"),
                recipient=str(rec.get("recipient") or ""),
                phone=str(rec.get("customer_phone") or ""),
                delivery=str(rec.get("delivery") or ""),
                platform=str(rec.get("platform") or ""),
                chat=str(rec.get("chat") or ""),
                source="legacy_migration",
                notify_now=True,
            )
            if result.get("status") == "ok":
                migrated += 1
            else:
                errors += 1
        return {"status": "ok", "migrated": migrated, "skipped": skipped, "errors": errors}


__all__ = ["SalesLifecycle", "WAITING_SHIPMENT", "TRACKING_ACTIVE", "FINAL_STATUSES"]
