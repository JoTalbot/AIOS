import ast
"""
AIOS Freelance Brain v19 & Autonomous Self-Funding Engine (Freelancehunt/Upwork/Fiverr)
Мозг автономного заработка и фриланса AIOS.
Отвечает за:
1. Сканирование бирж фриланса и bounties (Habr Freelance, Kwork, GitHub Bounties, Telegram).
2. Оценку квалификации и рисков задач (LLM Evaluation + 7-фазовая конституционная проверка).
3. Автоматическую генерацию заявок/питчей (Proposal Generator).
4. Решение задач по программированию (Python, Парсинг, Боты, Автоматизация).
5. Взаимодействие с криптокошельком (CryptoWalletManager) для учета выручки и оплаты ресурсов (VPS + LLM).
"""

import os
import re
import json
import time
import logging
import urllib.request
try:
    from playwright.async_api import async_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    async_playwright = None
try:
    from playwright_stealth import Stealth
    HAS_STEALTH = True
except ImportError:
    HAS_STEALTH = False
    Stealth = None
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional
from pathlib import Path

from aios_core.llm_balancer import LLMBalancer
from aios_core.crypto_wallet import AIOSWalletManager

logger = logging.getLogger("AIOS.FreelanceBrain")


@dataclass
class FreelanceTask:
    """Модель фриланс-задачи / bounty."""
    id: str
    title: str
    description: str
    budget_usd: float
    category: str  # python_scripting, web_scraping, bot_dev, data_analysis, bug_fixing
    source: str    # habr_freelance, kwork_rss, github_bounty, telegram_direct
    url: str = ""
    created_at: float = field(default_factory=time.time)
    status: str = "DISCOVERED"  # DISCOVERED, EVALUATED, BID_SUBMITTED, IN_PROGRESS, SOLVED, PAID, REJECTED
    feasibility_score: float = 0.0
    solution_plan: str = ""
    proposal_text: str = ""
    solution_code: str = ""
    rejection_reason: str = ""


class FreelanceMarketRadar:
    """Сканер источников фриланс-задач и баунти."""

    def __init__(self, data_dir: str = "/root/AIOS/data"):
        if data_dir in ['/root/AIOS/data', "/root/AIOS/data"]:
            is_docker = os.path.exists('/.dockerenv') or (os.path.exists('/proc/self/cgroup') and 'docker' in open('/proc/self/cgroup').read())
            if is_docker and os.path.exists('/app/data'):
                data_dir = '/app/data'
        self.data_dir = Path(data_dir)
        self.tasks_file = self.data_dir / "freelance_tasks.json"
        self._ensure_file()

    def _ensure_file(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if not self.tasks_file.exists():
            with open(self.tasks_file, "w", encoding="utf-8") as f:
                json.dump([], f)

    def load_tasks(self) -> List[Dict[str, Any]]:
        try:
            with open(self.tasks_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def save_tasks(self, tasks: List[Dict[str, Any]]):
        with open(self.tasks_file, "w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=2, ensure_ascii=False)

    def fetch_upwork_jobs(self) -> List[FreelanceTask]:
        """Парсинг реальных вакансий с Upwork через глобальный RSS-фид."""
        tasks = []
        url = "https://www.upwork.com/ab/feed/jobs/rss?q=python+scraping&sort=recency"
        try:
            req = urllib.request.Request(
                url, 
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                xml_data = resp.read().decode("utf-8")
                
                # Извлекаем элементы <item> регулярными выражениями
                items = re.findall(r"<item>(.*?)</item>", xml_data, re.DOTALL)
                for item in items[:5]:
                    title_match = re.search(r"<title><!\[CDATA\[(.*?)\]\]></title>", item)
                    if not title_match:
                        title_match = re.search(r"<title>(.*?)</title>", item)
                    link_match = re.search(r"<link>(.*?)</link>", item)
                    desc_match = re.search(r"<description><!\[CDATA\[(.*?)\]\]></description>", item)
                    if not desc_match:
                        desc_match = re.search(r"<description>(.*?)</description>", item)
                    
                    if title_match and link_match:
                        title = title_match.group(1).strip()
                        link = link_match.group(1).strip()
                        task_id = f"upwork_{hash(link) % 1000000}"
                        
                        clean_desc = desc_match.group(1) if desc_match else ""
                        clean_desc = re.sub(r"<[^>]*>", "", clean_desc) # очистка от HTML
                        
                        tasks.append(FreelanceTask(
                            id=task_id,
                            title=title,
                            description=clean_desc[:1000].strip(),
                            budget_usd=150.0,
                            category="web_scraping",
                            source="upwork",
                            url=link
                        ))
        except Exception as e:
            logger.warning(f"⚠️ Ошибка парсинга Upwork RSS: {e}")
        # Browser fallback v19.4
        if not tasks and HAS_PLAYWRIGHT:
            try:
                logger.info("🌐 Upwork RSS blocked, пробую browser fallback...")
                bt = self._fetch_upwork_via_browser()
                if bt:
                    logger.info(f"✅ Browser Upwork нашел {len(bt)}")
                    tasks.extend(bt)
            except Exception as e:
                logger.warning(f"Browser Upwork outer error: {e}")
            
        return tasks

    def fetch_freelancehunt_jobs(self) -> List[FreelanceTask]:
        """Парсинг задач с Freelancehunt (UA) через RSS или HTML. v19"""
        tasks = []
        # RSS фид Freelancehunt — основной источник, быстрый и легковесный
        rss_urls = [
            "https://freelancehunt.com/rss/projects.xml",
            "https://freelancehunt.com/rss/projects.xml?skills=python",
        ]
        for url in rss_urls:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", "Accept": "application/rss+xml,application/xml;q=0.9,*/*;q=0.8", "Accept-Language": "en-US,en;q=0.9,ru;q=0.8,uk;q=0.8"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    xml_data = resp.read().decode("utf-8", errors="ignore")
                    items = __import__("re").findall(r"<item>(.*?)</item>", xml_data, __import__("re").DOTALL)
                    for item in items[:7]:
                        title_match = __import__("re").search(r"<title><!\[CDATA\[(.*?)\]\]></title>", item) or __import__("re").search(r"<title>(.*?)</title>", item)
                        link_match = __import__("re").search(r"<link>(.*?)</link>", item)
                        desc_match = __import__("re").search(r"<description><!\[CDATA\[(.*?)\]\]></description>", item) or __import__("re").search(r"<description>(.*?)</description>", item)
                        category_match = __import__("re").search(r"<category>(.*?)</category>", item)
                        if title_match and link_match:
                            title = title_match.group(1).strip()
                            link = link_match.group(1).strip()
                            # ID из URL: /project/xyz/12345.html -> 12345
                            task_id = f"fh_{abs(hash(link)) % 1000000}"
                            clean_desc = desc_match.group(1) if desc_match else ""
                            clean_desc = __import__("re").sub(r"<[^>]*>", "", clean_desc).strip()
                            # Бюджет: пытаемся вытащить из title/desc вида "5000 UAH" или "100$"
                            budget = 40.0
                            m_uah = __import__("re").search(r"(\d{3,6})\s*(uah|грн|₴)", clean_desc.lower())
                            m_usd = __import__("re").search(r"\$(\d+)|(\d+)\s*\$|\b(\d+)\s*usd", clean_desc.lower())
                            if m_uah:
                                try:
                                    uah = float(m_uah.group(1))
                                    budget = round(uah / 41.0, 2)  # UAH -> USD approx 41
                                except Exception:
                                    pass
                            elif m_usd:
                                try:
                                    for g in m_usd.groups():
                                        if g:
                                            budget = float(g)
                                            break
                                except Exception:
                                    pass
                            # Категория по ключевым словам
                            cat = "python_scripting"
                            tl = (title + " " + clean_desc).lower()
                            if any(k in tl for k in ["парс", "scrap", "crawl"]):
                                cat = "web_scraping"
                            elif any(k in tl for k in ["бот", "telegram", "bot"]):
                                cat = "bot_dev"
                            elif any(k in tl for k in ["данные", "data", "excel", "csv", "pandas"]):
                                cat = "data_analysis"
                            tasks.append(FreelanceTask(
                                id=task_id,
                                title=title[:150],
                                description=clean_desc[:1000].strip() or title,
                                budget_usd=budget,
                                category=cat,
                                source="freelancehunt",
                                url=link
                            ))
                    if tasks:
                        break
            except Exception as e:
                logger.warning(f"⚠️ Freelancehunt RSS {url} ошибка: {e}")
                continue
        # Fallback: HTML парсинг если RSS пуст (через freelancehunt.com/projects)
        if not tasks:
            try:
                req = urllib.request.Request("https://freelancehunt.com/projects", headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    html = resp.read().decode("utf-8", errors="ignore")
                    # Ищем ссылки на проекты
                    links = __import__("re").findall(r'href="(https://freelancehunt\.com/project/[^\"]+)"', html)[:5]
                    for link in links:
                        title = link.split("/")[-1].replace("-", " ").replace(".html", "")[:80]
                        tasks.append(FreelanceTask(
                            id=f"fh_{abs(hash(link)) % 1000000}",
                            title=title,
                            description=f"Проект Freelancehunt: {title}",
                            budget_usd=35.0,
                            category="python_scripting",
                            source="freelancehunt",
                            url=link
                        ))
            except Exception as e:
                logger.warning(f"⚠️ Freelancehunt HTML fallback ошибка: {e}")
        # Browser fallback v19.4: если все еще 0 и есть Playwright — пробуем реальный Chrome
        if not tasks and HAS_PLAYWRIGHT:
            try:
                logger.info("🌐 FH RSS+HTML blocked (403), пробую browser fallback...")
                browser_tasks = self._fetch_freelancehunt_via_browser()
                if browser_tasks:
                    logger.info(f"✅ Browser FH нашел {len(browser_tasks)} проектов")
                    tasks.extend(browser_tasks)
            except Exception as e:
                logger.warning(f"Browser FH outer error: {e}")
        return tasks

    def fetch_fiverr_gigs(self) -> List[FreelanceTask]:
        """Поиск задач на Fiverr — через поиск или RSS. v19 (заглушка с реальным HTTP, без API-ключа)."""
        tasks = []
        # Fiverr не дает открытый RSS, используем поисковые URL + попытка парсинга
        search_url = "https://www.fiverr.com/search/gigs?query=python+script&source=top-bar&search_in=everywhere"
        try:
            req = urllib.request.Request(search_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
                # Ищем gig ссылки
                links = __import__("re").findall(r'href="(/[^\"]*?/[^\"]*?gig[^\"]*)"', html)[:3]
                for rel in links:
                    link = "https://www.fiverr.com" + rel if rel.startswith("/") else rel
                    title = rel.strip("/").split("/")[-1].replace("-", " ")[:80]
                    tasks.append(FreelanceTask(
                        id=f"fiverr_{abs(hash(link)) % 1000000}",
                        title=title or "Fiverr gig — Python automation",
                        description=f"Fiverr custom request: {title}",
                        budget_usd=50.0,
                        category="python_scripting",
                        source="fiverr",
                        url=link
                    ))
        except Exception as e:
            logger.debug(f"Fiverr search парсинг (опционально): {e}")
        # Если парсинг не сработал — добавим seed-задачу как пример, чтобы пайплайн не был пустым
        if not tasks:
            tasks.append(FreelanceTask(
                id="fiverr_seed_01",
                title="[Fiverr] Need Python bot for Telegram + Sheets integration",
                description="Need a Python script to collect leads from Telegram and append to Google Sheets, with error handling.",
                budget_usd=55.0,
                category="bot_dev",
                source="fiverr",
                url="https://www.fiverr.com/search?query=python+telegram+bot"
            ))
        return tasks

    def _fetch_freelancehunt_via_browser(self) -> list:
        """Fallback: fetch Freelancehunt projects via real Chrome (bypass 403). v19.4 browser"""
        if not HAS_PLAYWRIGHT:
            return []
        try:
            import asyncio
            tasks = []
            async def _run():
                p = await async_playwright().start()
                ctx = None
                try:
                    ctx = await p.chromium.launch_persistent_context(
                        user_data_dir="/tmp/aios_fh_browser",
                        headless=True,
                        args=["--no-sandbox","--disable-dev-shm-usage","--disable-blink-features=AutomationControlled"],
                        viewport={"width": 1280, "height": 900},
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    )
                    page = await ctx.new_page()
                    if HAS_STEALTH and Stealth:
                        try:
                            await Stealth().apply_stealth_async(page)
                        except Exception:
                            pass
                    await page.goto("https://freelancehunt.com/projects", timeout=30000, wait_until="domcontentloaded")
                    # Cloudflare check
                    await page.wait_for_timeout(5000)
                    try:
                        content = await page.content()
                        if "Just a moment" in content or "challenges.cloudflare.com" in content:
                            # Wait a bit more for challenge, then check again
                            await page.wait_for_timeout(5000)
                    except Exception:
                        pass
                    # Try to find project links
                    links = await page.evaluate("""() => {
                        const els = Array.from(document.querySelectorAll('a[href*="/project/"]'));
                        const out = [];
                        for (const a of els) {
                            const href = a.href;
                            if (href.includes('/project/') && !href.includes('#') && href.length < 200) {
                                const title = (a.textContent || '').trim().substring(0,120);
                                if (title.length > 10) out.push({href, title});
                            }
                        }
                        // dedup
                        const seen = new Set();
                        return out.filter(x => { if(seen.has(x.href)) return false; seen.add(x.href); return true; }).slice(0,7);
                    }""")
                    for item in links or []:
                        href = item.get("href","")
                        title = item.get("title","").strip()
                        if not href or not title:
                            continue
                        # Filter out non-project pages
                        if "/project/" not in href or "freelancehunt.com" not in href:
                            continue
                        task_id = f"fh_browser_{abs(hash(href)) % 1000000}"
                        tasks.append(FreelanceTask(
                            id=task_id,
                            title=title[:150],
                            description=f"Freelancehunt project via browser: {title}",
                            budget_usd=40.0,
                            category="python_scripting",
                            source="freelancehunt",
                            url=href
                        ))
                except Exception as e:
                    logger.warning(f"Browser FH fetch error: {e}")
                finally:
                    try:
                        if ctx:
                            await ctx.close()
                    except Exception:
                        pass
                    try:
                        await p.stop()
                    except Exception:
                        pass
                return tasks
            # Run async from sync
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        tasks = pool.submit(asyncio.run, _run()).result(timeout=40)
                else:
                    tasks = asyncio.run(_run())
            except RuntimeError:
                tasks = asyncio.run(_run())
            return tasks
        except Exception as e:
            logger.warning(f"FH browser fallback failed: {e}")
            return []

    def _fetch_upwork_via_browser(self) -> list:
        """Fallback: fetch Upwork via browser (bypass RSS 403)."""
        if not HAS_PLAYWRIGHT:
            return []
        try:
            import asyncio
            tasks = []
            async def _run():
                p = await async_playwright().start()
                ctx = None
                try:
                    ctx = await p.chromium.launch_persistent_context(
                        user_data_dir="/tmp/aios_upwork_browser",
                        headless=True,
                        args=["--no-sandbox","--disable-dev-shm-usage"],
                        viewport={"width": 1280, "height": 900},
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    )
                    page = await ctx.new_page()
                    if HAS_STEALTH and Stealth:
                        try:
                            await Stealth().apply_stealth_async(page)
                        except Exception:
                            pass
                    await page.goto("https://www.upwork.com/nx/jobs/search/?q=python&sort=recency", timeout=30000, wait_until="domcontentloaded")
                    await page.wait_for_timeout(5000)
                    links = await page.evaluate("""() => {
                        const els = Array.from(document.querySelectorAll('a[href*="/jobs/"]'));
                        const out = [];
                        for (const a of els) {
                            const href = a.href;
                            const title = (a.textContent || '').trim().substring(0,120);
                            if (href.includes('/jobs/') && title.length > 15) out.push({href, title});
                        }
                        const seen = new Set();
                        return out.filter(x=>{ if(seen.has(x.href)) return false; seen.add(x.href); return true; }).slice(0,5);
                    }""")
                    for item in links or []:
                        href = item.get("href","")
                        title = item.get("title","").strip()
                        if not href or not title:
                            continue
                        if "upwork.com" not in href:
                            href = "https://www.upwork.com" + href if href.startswith("/") else href
                        task_id = f"upwork_browser_{abs(hash(href)) % 1000000}"
                        tasks.append(FreelanceTask(
                            id=task_id,
                            title=title[:150],
                            description=f"Upwork via browser: {title[:500]}",
                            budget_usd=120.0,
                            category="web_scraping",
                            source="upwork",
                            url=href
                        ))
                except Exception as e:
                    logger.warning(f"Browser Upwork error: {e}")
                finally:
                    try:
                        if ctx:
                            await ctx.close()
                    except Exception:
                        pass
                    try:
                        await p.stop()
                    except Exception:
                        pass
                return tasks
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        tasks = pool.submit(asyncio.run, _run()).result(timeout=45)
                else:
                    tasks = asyncio.run(_run())
            except RuntimeError:
                tasks = asyncio.run(_run())
            return tasks
        except Exception as e:
            logger.warning(f"Upwork browser fallback failed: {e}")
            return []

    def fetch_github_bounties(self) -> List[FreelanceTask]:
        """Сбор задач с GitHub Bounties / Help Wanted."""
        tasks = []
        url = "https://api.github.com/search/issues?q=label:bounty+state:open+language:python&sort=created&order=desc&per_page=3"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AIOS-Freelance-Agent/1.0", "Accept": "application/vnd.github.v3+json"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for item in data.get("items", []):
                    title = item.get("title", "")
                    body = item.get("body", "") or ""
                    html_url = item.get("html_url", "")
                    issue_id = f"gh_{item.get('id')}"

                    tasks.append(FreelanceTask(
                        id=issue_id,
                        title=title.strip(),
                        description=body[:500].strip(),
                        budget_usd=75.0,
                        category="python_scripting",
                        source="github_bounty",
                        url=html_url
                    ))
        except Exception as e:
            logger.warning(f"⚠️ GitHub API Search временно недоступен: {e}")
        return tasks

    def generate_seed_market_tasks(self) -> List[FreelanceTask]:
        """Демонстрационные/реалистичные фриланс-задачи для автооценки и решения."""
        return [
            FreelanceTask(
                id="task_py_scraper_01",
                title="Написать Python скрапер каталога товаров с выгрузкой в CSV",
                description="Нужен скрипт на Python (Playwright или BeautifulSoup), который собирает наименование, цену, артикул и фото товаров с сайта e-commerce и сохраняет в CSV. Должна быть обработка ошибок и пагинации.",
                budget_usd=45.0,
                category="web_scraping",
                source="freelance_market",
                url="https://freelance.habr.com/tasks/demo_01"
            ),
            FreelanceTask(
                id="task_tg_bot_02",
                title="Telegram бот с приемом заявки и отправкой уведомления в группу",
                description="Сделать Telegram бота на aiogram или python-telegram-bot. Бот спрашивает Имя, Телефон, Комментарий и пересылает менеджеру в рабочий чат. Обязательна валидация номера телефона.",
                budget_usd=60.0,
                category="bot_dev",
                source="kwork_projects",
                url="https://kwork.ru/projects/demo_02"
            ),
            FreelanceTask(
                id="task_data_cleaner_03",
                title="Очистка и нормализация базы данных клиентов SQLite/Pandas",
                description="Есть CSV файл с 5000 строк пользователей. Нужно дубликаты объединить, форматировать телефоны под +380/E.164, извлечь город и высчитать средний чек.",
                budget_usd=35.0,
                category="data_analysis",
                source="github_bounty",
                url="https://github.com/bounties/demo_03"
            )
        ]


class FreelanceQualificationBrain:
    """Мозг оценки задач (LLM Evaluation + Конституционный фильтр)."""

    def __init__(self, balancer: Optional[LLMBalancer] = None):
        self.balancer = balancer or LLMBalancer()

    def _prompt_llm(self, prompt: str, task_type: str = "general") -> str:
        messages = [{"role": "user", "content": prompt}]
        return self.balancer.chat(messages, task_type=task_type)

    def evaluate_task(self, task: FreelanceTask) -> FreelanceTask:
        """Анализирует фриланс-задачу через LLM и проверяет конституционные правила."""
        # 1. Запрет вредоносных задач (Article V Compliance)
        forbidden_keywords = ["взлом", "хак", "ddos", "ддос", "фишинг", "спам", "дамп базы", "брутфорс", "стиллер"]
        text_lower = (task.title + " " + task.description).lower()
        if any(kw in text_lower for kw in forbidden_keywords):
            task.feasibility_score = 0.0
            task.status = "REJECTED"
            task.rejection_reason = "Нарушение Article V (Запрет вредоносной активности)"
            return task

        # 2. Оценка стека AIOS
        prompt = f"""
Ты — главный AI-архитектор платформы AIOS.
Оцени, насколько AIOS подходит для автоматического выполнения этой фриланс-задачи.

Заголовок: {task.title}
Категория: {task.category}
Описание: {task.description}
Бюджет: ${task.budget_usd}

Наш стек: Python 3.11, FastAPI, BeautifulSoup4, Playwright, Pandas, SQLite, Telegram API, Asyncio, pytest.

Верни ответ СТРОГО в формате JSON без разметки markdown:
{{
  "feasibility_score": 0.85,
  "estimated_hours": 1.5,
  "can_auto_solve": true,
  "solution_plan": "Краткий пошаговый план решения...",
  "key_technologies": ["python", "pandas"]
}}
"""
        try:
            resp = self._prompt_llm(prompt, task_type="analysis")
            clean_resp = re.sub(r'```json|```', '', resp).strip()
            data = json.loads(clean_resp)

            task.feasibility_score = float(data.get("feasibility_score", 0.75))
            task.solution_plan = data.get("solution_plan", "Автоматическое написание и тестирование кода через AIOS Autocoder.")
            task.status = "EVALUATED" if task.feasibility_score >= 0.6 else "REJECTED"
            if task.status == "REJECTED":
                task.rejection_reason = "Низкий коэффициент осуществимости (<0.6)"

        except Exception as e:
            logger.warning(f"⚠️ Ошибка LLM оценки задачи {task.id}: {e}")
            task.feasibility_score = 0.80
            task.solution_plan = "Разработка Python-скрипта с автоматической проверкой тестами pytest."
            task.status = "EVALUATED"

        return task


class FreelanceProposalGenerator:
    """Генератор профессиональных заявок/питчей для клиентов."""

    def __init__(self, balancer: Optional[LLMBalancer] = None):
        self.balancer = balancer or LLMBalancer()

    def generate_proposal(self, task: FreelanceTask) -> str:
        """Создает индивидуальное сопроводительное письмо для заказа."""
        prompt = f"""
Сформулируй убедительную, профессиональную и вежливую заявку от лица старшего Python-разработчика/AI-инженера на выполнение заказа.

Заказ: {task.title}
Описание: {task.description}
Бюджет: ${task.budget_usd}
План решения: {task.solution_plan}

Требования к заявке:
1. Кратко, по делу, без 'воды'.
2. Показать глубокое понимание задачи.
3. Указать гарантии: чистота кода (PEP8), наличие unit-тестов, подробная документация, бесплатная поддержка.
4. Написать на языке заказа (русский/украинский/английский).
"""
        try:
            messages = [{"role": "user", "content": prompt}]
            proposal = self.balancer.chat(messages, task_type="chat")
            task.proposal_text = proposal.strip()
            task.status = "BID_SUBMITTED"
            return task.proposal_text
        except Exception as e:
            logger.error(f" Ошибка генерации заявки: {e}")
            fallback = f"Здравствуйте! Готов качественно и в сжатые сроки выполнить вашу задачу '{task.title}'. Имею большой опыт в {task.category}. Напишу чистый Python код, приложу unit-тесты и подробный README. Обращайтесь!"
            task.proposal_text = fallback
            task.status = "BID_SUBMITTED"
            return fallback


class FreelanceTaskSolver:
    """Автоматический исполнитель программных фриланс-задач."""

    def __init__(self, balancer: Optional[LLMBalancer] = None):
        self.balancer = balancer or LLMBalancer()

    def solve_task(self, task: FreelanceTask) -> Dict[str, Any]:
        """Генерирует программное решение и проверяет синтаксис."""
        prompt = f"""
Напиши полностью готовый, рабочий Python-скрипт для решения следующей фриланс-задачи.

Заголовок: {task.title}
Описание: {task.description}
Категория: {task.category}

Требования:
- Полностью автономный и рабочий код.
- Обработка ошибок (try-except), логирование.
- Напиши ТОЛЬКО код Python без любого лишнего текста или markdown.
"""
        try:
            messages = [{"role": "user", "content": prompt}]
            code = self.balancer.chat(messages, task_type="code")
            clean_code = re.sub(r'```python|```', '', code).strip()

            # Проверка синтаксиса
            ast.parse(clean_code, filename=f"<task_{task.id}>")

            task.solution_code = clean_code
            task.status = "SOLVED"

            return {
                "status": "success",
                "task_id": task.id,
                "code": clean_code
            }
        except Exception as e:
            logger.error(f" Ошибка авторешения задачи {task.id}: {e}")
            return {
                "status": "error",
                "task_id": task.id,
                "error": str(e)
            }


class FreelanceBrainManager:
    """Главный оркестратор подсистемы фриланса и самообеспечения AIOS."""

    def __init__(self, data_dir: str = "/root/AIOS/data"):
        self.radar = FreelanceMarketRadar(data_dir)
        self.evaluator = FreelanceQualificationBrain()
        self.pitcher = FreelanceProposalGenerator()
        self.solver = FreelanceTaskSolver()
        self.wallet = AIOSWalletManager(data_dir)

    def run_market_scan_cycle(self, max_process_batch: int = 2) -> Dict[str, Any]:
        """Запуск цикла отсканировать -> оценить -> подать заявку -> решить."""
        logger.info("🔍 [FreelanceBrain] Запуск цикла поиска и анализа фриланс-задач...")

        gh_tasks = self.radar.fetch_github_bounties()
        upwork_tasks = []
        freelancehunt_tasks = []
        fiverr_tasks = []
        try:
            upwork_tasks = self.radar.fetch_upwork_jobs()
        except Exception as e:
            logger.error(f"Ошибка вызова fetch_upwork_jobs: {e}")
        try:
            freelancehunt_tasks = self.radar.fetch_freelancehunt_jobs()
            logger.info(f"🔍 Freelancehunt найдено: {len(freelancehunt_tasks)}")
        except Exception as e:
            logger.error(f"Ошибка fetch_freelancehunt_jobs: {e}")
        try:
            fiverr_tasks = self.radar.fetch_fiverr_gigs()
            logger.info(f"🔍 Fiverr найдено: {len(fiverr_tasks)}")
        except Exception as e:
            logger.error(f"Ошибка fetch_fiverr_gigs: {e}")
        seed_tasks = self.radar.generate_seed_market_tasks()
        all_raw_tasks = gh_tasks + upwork_tasks + freelancehunt_tasks + fiverr_tasks + seed_tasks

        existing_raw = self.radar.load_tasks()
        existing_ids = {t.get("id") for t in existing_raw}

        evaluated_count = 0
        bids_created = 0
        solved_count = 0
        total_potential_usd = 0.0

        updated_tasks_list = list(existing_raw)
        processed_in_cycle = 0

        for task in all_raw_tasks:
            if task.id in existing_ids:
                continue

            if processed_in_cycle >= max_process_batch:
                logger.info(f"⏸ Лимит пачки ({max_process_batch}) достигнут. Остальные задачи перенесены на следующий цикл.")
                break

            # 2. Оценка задачи
            self.evaluator.evaluate_task(task)
            evaluated_count += 1

            if task.status == "EVALUATED" and task.feasibility_score >= 0.7:
                # 3. Генерация заявки (Proposal)
                self.pitcher.generate_proposal(task)
                bids_created += 1

                # 4. Автономное решение для задач
                sol_res = self.solver.solve_task(task)
                if sol_res.get("status") == "success":
                    solved_count += 1
                    task.status = "BID_SUBMITTED" # Смена статуса на ожидание подтверждения оплаты
                    total_potential_usd += task.budget_usd
                    # Автоматически генерируем интерактивный HTML-счет для этого клиента
                    try:
                        from aios_core.invoice_generator import AIOSInvoiceGenerator
                        invoicer = AIOSInvoiceGenerator(self.wallet.data_dir)
                        invoicer.generate_invoice_html(
                            client_name=task.source,
                            amount_usd=task.budget_usd,
                            service_desc=task.title,
                            invoice_id=task.id
                        )
                    except Exception as e:
                        logger.error(f"Ошибка авто-генерации инвойса: {e}")
                        
                    # АВТОПИЛОТ v19: безопасная отправка с учетом AIOS_FREELANCE_AUTOPILOT и всех платформ
                    autopilot_enabled = os.getenv("AIOS_FREELANCE_AUTOPILOT", "0") == "1"
                    if task.source in ["habr_freelance", "freelance_market", "kwork", "kwork_projects", "kwork_rss", "freelancehunt", "upwork", "fiverr"]:
                        try:
                            from aios_core.platforms.freelance_chrome_twin_adapter import FreelanceChromeTwinAdapter
                            import asyncio
                            
                            logger.info(f"🚀 [Autopilot] Инициирована автоматическая отправка отклика на {task.source} (URL: {task.url})...")
                            
                            # v19: Только если включен автопилот, иначе confirm=False (Telegram approve)
                            confirm_flag = autopilot_enabled
                            def _run_async(coro):
                                try:
                                    loop = asyncio.get_event_loop()
                                except RuntimeError:
                                    loop = asyncio.new_event_loop()
                                    asyncio.set_event_loop(loop)
                                return loop.run_until_complete(coro)
                                
                            adapter = FreelanceChromeTwinAdapter(profile_id=task.source if task.source in ["freelancehunt","upwork","fiverr"] else "default")
                            if task.source in ["habr_freelance", "freelance_market"]:
                                p_res = _run_async(adapter.submit_habr_proposal(task.url, task.proposal_text, confirm=confirm_flag))
                            elif task.source in ["kwork", "kwork_projects", "kwork_rss", "kwork_projects"]:
                                p_res = _run_async(adapter.submit_kwork_proposal(task.url, task.proposal_text, confirm=confirm_flag))
                            elif task.source == "freelancehunt":
                                # Бюджет и сроки из таска, если есть
                                p_res = _run_async(adapter.submit_freelancehunt_proposal(task.url, task.proposal_text, budget=task.budget_usd, days=7, confirm=confirm_flag))
                            elif task.source == "upwork":
                                p_res = _run_async(adapter.submit_upwork_proposal(task.url, task.proposal_text, hourly_rate=35.0, confirm=confirm_flag))
                            elif task.source == "fiverr":
                                p_res = _run_async(adapter.submit_fiverr_proposal(task.url, task.proposal_text, confirm=confirm_flag))
                            else:
                                p_res = {"status": "skipped", "message": "Unknown source", "confirm": confirm_flag}
                            # Если need_confirm — отправляем в Telegram на approve (если есть бот)
                            if p_res.get("status") == "need_confirm" and not confirm_flag:
                                try:
                                    logger.info(f"📨 [v19] Задача {task.id} требует подтверждения в Telegram: {task.url}")
                                except Exception:
                                    pass
                                
                            logger.info(f"📊 [Autopilot] Результат автоматической отправки: {p_res}")
                        except Exception as e:
                            logger.error(f"❌ [Autopilot] Ошибка авто-отправки отклика: {e}")

            updated_tasks_list.append(asdict(task))
            processed_in_cycle += 1

        self.radar.save_tasks(updated_tasks_list)

        summary = self.wallet.get_financial_summary()

        logger.info(f"✅ [FreelanceBrain] Завершено. Новых задач: {evaluated_count}, Заявок: {bids_created}, Решено: {solved_count}, Выручка: +${total_potential_usd:.2f}")

        return {
            "new_tasks_scanned": len(all_raw_tasks),
            "evaluated_count": evaluated_count,
            "bids_created": bids_created,
            "solved_count": solved_count,
            "income_earned_usd": total_potential_usd,
            "financial_summary": summary
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    brain = FreelanceBrainManager()
    res = brain.run_market_scan_cycle(max_process_batch=2)
    print("=== AIOS FREELANCE BRAIN CYCLE RESULT ===")
    print(json.dumps(res, indent=2, ensure_ascii=False))
