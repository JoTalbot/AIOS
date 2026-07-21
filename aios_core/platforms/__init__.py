"""AIOS Platforms — масштабируемый реестр маркетплейс-приложений и профилей.

Архитектура «платформа → профили» рассчитана на тысячи приложений,
аналогичных OLX: каждое приложение описывается дескриптором
(:class:`PlatformDescriptor`), каждый аккаунт — профилем
(:class:`Profile`) со своим устройством (ADB serial) и своим хранилищем
(``data/<platform>/<profile>.sqlite``).

CLI и REST API разрешают контекст работы через единый резолвер:
явный выбор → переменная окружения ``AIOS_PROFILE`` → профиль по умолчанию
платформы → встроенный эфемерный ``default``.
"""

from .apkfetch import fetch_apk, resolve_apk
from .advise import advise_drafts, reply_draft
from .bootup import bootup_platform
from .catalog import load_catalog, load_catalog_file
from .compliance import compliance_block, compliance_guard, rate_limit_hours
from .descriptor import (
    PlatformDescriptor,
    get_platform,
    list_platforms,
    register_platform,
)
from .dashboard import dashboard_html
from .devices import DevicePool
from .fleetsched import FleetScheduler
from .videocards import HintVideoParser, VideoCard, video_parser_for
from .calibrate import (
    CalibrationAdvisor,
    DetailCalibrationAdvisor,
    hints_to_yaml_doc,
    merge_hints,
    write_hints_to_descriptor,
)
from .fleet import PoolMonitor, ensure_device
from .gateway import ShardGateway, ShardHealthMonitor
from .parsergen import (
    build_parser,
    extract_markers,
    generate_parser_source,
    parser_for,
    write_parser,
)
from .pointdrive import PointDrive
from .profile import Profile
from .recipe import calibration_recipe
from .reelscout import ReelsCollector, ReelsTabDriver, reels_driver_for
from .regression import (
    check_platform_markers,
    diff_markers,
    drift_events_summary,
)
from .runtime_hints import (
    HintDetailParser,
    HintSender,
    chat_list_parser_for,
    detail_parser_for,
    load_hints_section,
)
from .resolver import (
    adb_for,
    resolve_profile,
    storage_for,
)
from .scaffold import inspect_apk, scaffold_from_apk, scaffold_platform
from .secrets import (
    load_secrets_file,
    required_secret,
    secret,
)
from .shardexec import ShardJobs, ShardJobWorker, default_handlers
from .shards import ShardRouter
from .store import ProfileStore

__all__ = [
    "DevicePool",
    "DetailCalibrationAdvisor",
    "FleetScheduler",
    "HintDetailParser",
    "HintSender",
    "HintVideoParser",
    "PlatformDescriptor",
    "PointDrive",
    "VideoCard",
    "PoolMonitor",
    "Profile",
    "ProfileStore",
    "ReelsCollector",
    "ReelsTabDriver",
    "reels_driver_for",
    "ShardRouter",
    "ShardJobs",
    "ShardJobWorker",
    "default_handlers",
    "CalibrationAdvisor",
    "ShardGateway",
    "ShardHealthMonitor",
    "adb_for",
    "advise_drafts",
    "bootup_platform",
    "build_parser",
    "calibration_recipe",
    "chat_list_parser_for",
    "dashboard_html",
    "check_platform_markers",
    "compliance_block",
    "compliance_guard",
    "detail_parser_for",
    "diff_markers",
    "drift_events_summary",
    "rate_limit_hours",
    "ensure_device",
    "extract_markers",
    "fetch_apk",
    "generate_parser_source",
    "hints_to_yaml_doc",
    "get_platform",
    "inspect_apk",
    "list_platforms",
    "load_catalog",
    "load_catalog_file",
    "load_hints_section",
    "load_secrets_file",
    "merge_hints",
    "parser_for",
    "register_platform",
    "reply_draft",
    "required_secret",
    "resolve_apk",
    "resolve_profile",
    "scaffold_from_apk",
    "scaffold_platform",
    "secret",
    "storage_for",
    "video_parser_for",
    "write_hints_to_descriptor",
    "write_parser",
]
