"""AutoWatch для произвольной платформы — движок OLX на descriptor+profile.

OLX-цикл заботы (`AutoWatch`: сбор подписок → алерты → снапшот своих →
застой → предложения) написан инъецируемо; этот модуль — универсальная
проводка для любой платформы каталога:

* **хранилище** — profile-scoped через резолвер
  (``data/<platform>/<profile>.sqlite``);
* **устройство** — ADB по ``device_serial`` профиля;
* **парсер карточек** — цепочка: явный → ``card_parser.CardParser``
  модуля платформы (codegen) → runtime ``parser_for`` из hints;
* **навигация** — опциональный драйв ``(package, query)->xml``
  (login/point-drive), вызывается перед сбором каждого запроса.

CLI: ``aios platforms autowatch --platform instagram --profile main
--query "кросівки" [--webhook URL] [--no-collect]``.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .descriptor import get_platform
from .parsergen import parser_for
from .resolver import adb_for, storage_for


def _module_card_parser(agent_module: str):
    """CardParser из codegen-модуля платформы, если он сгенерирован."""
    try:
        import importlib

        module = importlib.import_module(f"{agent_module}.card_parser")
        for attr in dir(module):
            candidate = getattr(module, attr)
            if isinstance(candidate, type) and attr.endswith("CardParser"):
                return candidate()
    except (ImportError, AttributeError):
        pass
    return None


def resolve_card_parser(platform_name: str, directory: str = "platforms"):
    """Цепочка резолва парсера карточек платформы.

    Codegen-класс модуля → runtime build_parser из hints дескриптора →
    честная ошибка с рецептом (bootup/calibrate).
    """
    descriptor = get_platform(platform_name)
    parser = _module_card_parser(descriptor.agent_module)
    if parser is not None:
        return parser
    try:
        return parser_for(platform_name, directory=directory)
    except ValueError as exc:
        raise ValueError(
            f"no card parser for '{platform_name}': run "
            "'aios platforms bootup ...' or calibrate --write "
            f"({exc})"
        ) from None


class _DrivenCollector:
    """Обёртка движка OLXCollector с pre-drive навигацией на запрос."""

    def __init__(
        self, adb, parser, driver=None, package: str = "", max_swipes: int = 40
    ):
        self._adb = adb
        self._parser = parser
        self._driver = driver
        self._package = package
        self.max_swipes = max_swipes

    def _engine(self):
        from aios_core.modules.olx.collector import OLXCollector

        return OLXCollector(
            adb=self._adb, parser=self._parser, max_swipes=self.max_swipes
        )

    def collect(self, query=None, max_cards=50, progress=None):
        if self._driver is not None:
            self._driver(self._package, query)
        return self._engine().collect(
            query=query,
            max_cards=max_cards,
            progress=progress,
        )

    def collect_to_storage(self, storage, query=None, max_cards=50, progress=None):
        if self._driver is not None:
            self._driver(self._package, query)
        return self._engine().collect_to_storage(
            storage,
            query=query,
            max_cards=max_cards,
            progress=progress,
        )


def autowatch_cycle(
    platform_name: str,
    profile_name: Optional[str] = None,
    queries: Optional[List[str]] = None,
    store=None,
    adb=None,
    parser=None,
    driver=None,
    notifier=None,
    webhook: Optional[str] = None,
    own_provider=None,
    max_cards: int = 50,
    collect: bool = True,
    directory: str = "platforms",
    min_age_days: float = 3.0,
) -> Dict[str, object]:
    """Один полный цикл AutoWatch для платформы/профиля.

    Returns:
        Отчёт цикла (collection/subscription_alerts/favorite_alerts/
        own_snapshot/stagnant/suggestions/notifications) как у OLX
        AutoWatch + блоки platform/profile/queries.
    """
    from aios_core.modules.olx.autowatch import AutoWatch
    from aios_core.modules.olx.notifier import WebhookNotifier
    from aios_core.modules.olx.watch import SubscriptionManager

    descriptor = get_platform(platform_name)
    storage = storage_for(platform_name, profile_name, store=store)
    adb = adb or adb_for(platform_name, profile_name, store=store)
    parser = parser or resolve_card_parser(platform_name, directory)
    notifier = notifier or WebhookNotifier(url=webhook)

    if queries is None:
        queries = sorted(
            {
                sub.get("query")
                for sub in SubscriptionManager(storage).list()
                if sub.get("query")
            }
        )

    collector = (
        _DrivenCollector(
            adb,
            parser,
            driver=driver,
            package=descriptor.android_package,
        )
        if collect
        else None
    )

    watcher = AutoWatch(
        storage,
        collector=collector,
        own_provider=own_provider,
        notifier=notifier,
        max_cards=max_cards,
    )
    report = watcher.run_cycle(
        queries=queries,
        collect=collect,
        min_age_days=min_age_days,
    )
    report["platform"] = platform_name
    if profile_name:
        report["profile"] = profile_name
    report["queries"] = queries
    return report
