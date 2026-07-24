"""AIOS CLI — Cross-platform comparison commands."""

import json


def _add_cross_platform_parsers(subparsers) -> None:
    """Register the ``cross-platform`` subcommand tree."""
    cp = subparsers.add_parser("cross-platform", help="Cross-platform price comparison (OLX ↔ Rozetka ↔ Prom ↔ Shafa)")
    cp_sub = cp.add_subparsers(dest="cp_command")

    def with_storages(p):
        """Add storage arguments for all platforms."""
        p.add_argument("--olx-db", default=None, help="OLX SQLite database file")
        p.add_argument("--rozetka-db", default=None, help="Rozetka SQLite database file")
        p.add_argument("--prom-db", default=None, help="Prom SQLite database file")
        p.add_argument("--shafa-db", default=None, help="Shafa SQLite database file")

    p = cp_sub.add_parser("compare", help="Compare products across platforms")
    p.add_argument("--query", default=None, help="Search query to filter products")
    p.add_argument("--min-similarity", type=float, default=0.6, help="Minimum title similarity (0-1)")
    with_storages(p)

    p = cp_sub.add_parser("product", help="Find same product on other platforms")
    p.add_argument("--fingerprint", required=True, help="Source product fingerprint")
    p.add_argument("--platform", required=True, choices=["olx", "rozetka", "prom", "shafa"], help="Source platform")
    with_storages(p)

    p = cp_sub.add_parser("arbitrage", help="Find arbitrage opportunities")
    p.add_argument("--min-spread", type=float, default=10.0, help="Minimum spread percentage for arbitrage")
    p.add_argument("--query", default=None, help="Search query to filter products")
    with_storages(p)

    # AI advisor v2
    adv = subparsers.add_parser("advisor-v2", help="AI advisor v2 — cross-platform recommendations")
    adv_sub = adv.add_subparsers(dest="advisor_v2_command")

    p = adv_sub.add_parser("recommend", help="Cross-platform buy/sell recommendation")
    p.add_argument("--title", required=True, help="Product title to analyze")
    p.add_argument("--min-spread", type=float, default=5.0, help="Minimum spread for arbitrage")
    with_storages(p)

    p = adv_sub.add_parser("predict", help="Price prediction for a product")
    p.add_argument("--fingerprint", required=True, help="Product fingerprint")
    p.add_argument("--platform", required=True, choices=["olx", "rozetka"], help="Platform")
    p.add_argument("--horizon", type=int, default=7, help="Prediction horizon in days")
    p.add_argument("--db", default=None, help="Database file")
    with_storages(p)

    p = adv_sub.add_parser("analyze", help="Full analysis: comparison + prediction + advice")
    p.add_argument("--title", required=True, help="Product title")
    p.add_argument("--fingerprint", default=None, help="Product fingerprint (optional)")
    p.add_argument("--platform", default="olx", choices=["olx", "rozetka"], help="Platform for prediction")
    with_storages(p)

    # Vector search
    vs = subparsers.add_parser("search", help="Vector search — semantic product matching")
    vs_sub = vs.add_subparsers(dest="search_command")

    p = vs_sub.add_parser("query", help="Search products by text query")
    p.add_argument("--text", required=True, help="Search query text")
    p.add_argument("--limit", type=int, default=10, help="Max results")
    p.add_argument("--platform", required=True, choices=["olx", "rozetka"], help="Platform to search")
    p.add_argument("--db", default=None, help="Database file")

    p = vs_sub.add_parser("similar", help="Find similar products")
    p.add_argument("--fingerprint", required=True, help="Reference product fingerprint")
    p.add_argument("--limit", type=int, default=10, help="Max results")
    p.add_argument("--platform", required=True, choices=["olx", "rozetka"], help="Platform to search")
    p.add_argument("--db", default=None, help="Database file")

    # Benchmarks thresholds
    bm = subparsers.add_parser("benchmarks", help="Performance benchmarks thresholds")
    bm_sub = bm.add_subparsers(dest="benchmarks_command")

    bm_sub.add_parser("list", help="List all benchmark thresholds")
    p = bm_sub.add_parser("check", help="Check if a benchmark passes its threshold")
    p.add_argument("--name", required=True, help="Benchmark name")
    p.add_argument("--actual-ms", type=float, required=True, help="Actual execution time in ms")


def _resolve_storages(args) -> dict:
    """Resolve storage instances from CLI arguments."""
    storages = {}
    from aios_core.modules.olx.storage import OLXStorage
    from aios_core.modules.rozetka.storage import RozetkaStorage

    for platform, attr in [("olx", "olx_db"), ("rozetka", "rozetka_db"), ("prom", "prom_db"), ("shafa", "shafa_db")]:
        db_path = getattr(args, attr, None)
        if db_path:
            if platform == "rozetka":
                storages[platform] = RozetkaStorage(db_path)
            else:
                storages[platform] = OLXStorage(db_path)

    return storages


def _run_cross_platform(args) -> bool:
    """Dispatch a cross-platform subcommand."""
    from aios_core.cross_platform_comparator import CrossPlatformComparator

    storages = _resolve_storages(args)
    if not storages:
        print(json.dumps({"error": "No storages configured — use --olx-db, --rozetka-db, etc."}, indent=2))
        return True

    comparator = CrossPlatformComparator(
        storages=storages,
        title_similarity_threshold=getattr(args, "min_similarity", 0.6),
    )

    if args.cp_command == "compare":
        groups = comparator.compare(query=args.query)
        print(json.dumps([g.to_dict() for g in groups], ensure_ascii=False, indent=2))
    elif args.cp_command == "product":
        group = comparator.compare_product(args.fingerprint, args.platform)
        if group:
            print(json.dumps(group.to_dict(), ensure_ascii=False, indent=2))
        else:
            print(json.dumps({"error": "No matches found"}, indent=2))
    elif args.cp_command == "arbitrage":
        opps = comparator.arbitrage_opportunities(min_spread_pct=getattr(args, "min_spread", 10.0))
        print(json.dumps([g.to_dict() for g in opps], ensure_ascii=False, indent=2))
    else:
        print(json.dumps({"error": "unknown cross-platform subcommand"}, indent=2))

    return True


def _run_advisor_v2(args) -> bool:
    """Dispatch an advisor-v2 subcommand."""
    from aios_core.ai_advisor_v2 import AICrossPlatformAdvisor
    from aios_core.cross_platform_comparator import CrossPlatformComparator
    from aios_core.modules.olx.storage import OLXStorage
    from aios_core.modules.rozetka.storage import RozetkaStorage

    storages = _resolve_storages(args)
    comparator = CrossPlatformComparator(storages=storages)
    advisor = AICrossPlatformAdvisor(comparator=comparator)

    if args.advisor_v2_command == "recommend":
        rec = advisor.recommend_cross_platform(args.title, min_spread_pct=getattr(args, "min_spread", 5.0))
        if rec:
            print(json.dumps(rec.__dict__, ensure_ascii=False, indent=2))
        else:
            print(json.dumps({"error": "Insufficient data for recommendation"}, indent=2))
    elif args.advisor_v2_command == "predict":
        platform = args.platform
        db_path = getattr(args, "db", None) or getattr(args, f"{platform}_db", None)
        if not db_path:
            db_path = ":memory:"
        storage = RozetkaStorage(db_path) if platform == "rozetka" else OLXStorage(db_path)
        pred = advisor.predict_price(storage, args.fingerprint, horizon_days=args.horizon)
        if pred:
            print(json.dumps(pred.__dict__, ensure_ascii=False, indent=2))
        else:
            print(json.dumps({"error": "Insufficient data for prediction"}, indent=2))
    elif args.advisor_v2_command == "analyze":
        storage = None
        if storages:
            first_key = next(iter(storages))
            storage = storages[first_key]
        result = advisor.full_analysis(args.title, storage=storage, fingerprint=getattr(args, "fingerprint", None))
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps({"error": "unknown advisor-v2 subcommand"}, indent=2))

    return True


def _run_search(args) -> bool:
    """Dispatch a vector search subcommand."""
    from aios_core.modules.olx.storage import OLXStorage
    from aios_core.modules.rozetka.storage import RozetkaStorage
    from aios_core.vector_search import VectorSearchEngine

    platform = args.platform
    db_path = getattr(args, "db", None)
    if not db_path:
        db_path = ":memory:"
    storage = RozetkaStorage(db_path) if platform == "rozetka" else OLXStorage(db_path)

    engine = VectorSearchEngine(storage=storage)
    engine.build_index()

    if args.search_command == "query":
        results = engine.search(args.text, limit=args.limit)
        print(json.dumps([r.to_dict() for r in results], ensure_ascii=False, indent=2))
    elif args.search_command == "similar":
        results = engine.find_similar(args.fingerprint, limit=args.limit)
        print(json.dumps([r.to_dict() for r in results], ensure_ascii=False, indent=2))
    else:
        print(json.dumps({"error": "unknown search subcommand"}, indent=2))

    return True


def _run_benchmarks(args) -> bool:
    """Dispatch a benchmarks subcommand."""
    from aios_core.benchmarks_thresholds import all_thresholds, check_threshold

    if args.benchmarks_command == "list":
        configs = all_thresholds()
        print(json.dumps(configs, indent=2))
    elif args.benchmarks_command == "check":
        result = check_threshold(args.name, args.actual_ms)
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps({"error": "unknown benchmarks subcommand"}, indent=2))

    return True
