"""CLI v10.0.0 — Price prediction ML, Image comparison, Fleet scheduler dispatch."""

from __future__ import annotations

import json

from aios_core.fleet_scheduler import (
    FleetDevice,
    FleetScheduler,
    SchedulingPolicy,
    TaskPriority,
)
from aios_core.image_comparison import (
    HashAlgorithm,
    ImageComparisonEngine,
)
from aios_core.price_prediction_ml import (
    PredictionModel,
    PricePoint,
    PricePredictionEngine,
)

# ─── Price Prediction ───

def _add_price_prediction_parsers(subparsers) -> None:
    """Add price-prediction subparsers."""
    pp = subparsers.add_parser("price-predict", help="ML price prediction models")
    pps = pp.add_subparsers(dest="pp_command")

    # predict
    p = pps.add_parser("predict", help="Predict price for a product")
    p.add_argument("--fingerprint", required=True, help="Product fingerprint")
    p.add_argument("--prices", required=True, nargs="+", type=float, help="Historical prices (space-separated)")
    p.add_argument("--model", choices=["linear", "poly2", "poly3", "sma", "wma", "ema", "ensemble"], default="ensemble")
    p.add_argument("--horizon", type=int, default=7, help="Days ahead to predict")
    p.add_argument("--format", choices=["json", "text"], default="json")

    # best
    p = pps.add_parser("best", help="Auto-select best prediction model")
    p.add_argument("--fingerprint", required=True)
    p.add_argument("--prices", required=True, nargs="+", type=float)
    p.add_argument("--horizon", type=int, default=7)

    # all
    p = pps.add_parser("all", help="Run all prediction models")
    p.add_argument("--fingerprint", required=True)
    p.add_argument("--prices", required=True, nargs="+", type=float)
    p.add_argument("--horizon", type=int, default=7)


def _run_price_predict(args) -> bool:
    """Execute price-predict CLI command."""
    engine = PricePredictionEngine()
    model_map = {
        "linear": PredictionModel.LINEAR,
        "poly2": PredictionModel.POLYNOMIAL_2,
        "poly3": PredictionModel.POLYNOMIAL_3,
        "sma": PredictionModel.SMA,
        "wma": PredictionModel.WMA,
        "ema": PredictionModel.EMA,
        "ensemble": PredictionModel.ENSEMBLE,
    }

    fp = getattr(args, "fingerprint", "fp_cli")
    prices = getattr(args, "prices", [])
    horizon = getattr(args, "horizon", 7)

    if not prices:
        print(json.dumps({"error": "No prices provided"}, ensure_ascii=False))
        return True

    history = [PricePoint(day=i, price=p) for i, p in enumerate(prices)]

    cmd = getattr(args, "pp_command", None)

    if cmd == "predict":
        model = model_map.get(getattr(args, "model", "ensemble"), PredictionModel.ENSEMBLE)
        result = engine.predict(fp, history, model, horizon)
        out = {
            "fingerprint": result.fingerprint,
            "current_price": result.current_price,
            "predicted_price": result.predicted_price,
            "trend": result.trend.value,
            "confidence": result.confidence,
            "model": result.model.value,
            "history_points": result.history_points,
            "horizon_days": result.horizon_days,
        }
        fmt = getattr(args, "format", "json")
        if fmt == "text":
            print(f"Prediction for {fp}:")
            print(f"  Current: {result.current_price:.2f} грн")
            print(f"  Predicted ({result.horizon_days}d): {result.predicted_price:.2f} грн")
            print(f"  Trend: {result.trend.value}")
            print(f"  Model: {result.model.value} (confidence: {result.confidence:.2f})")
        else:
            print(json.dumps(out, ensure_ascii=False))

    elif cmd == "best":
        result = engine.predict_best(fp, history, horizon)
        out = {
            "fingerprint": result.fingerprint,
            "predicted_price": result.predicted_price,
            "trend": result.trend.value,
            "confidence": result.confidence,
            "best_model": result.model.value,
        }
        print(json.dumps(out, ensure_ascii=False))

    elif cmd == "all":
        results = engine.predict_all(fp, history, horizon)
        out = []
        for r in results:
            out.append({
                "model": r.model.value,
                "predicted_price": r.predicted_price,
                "confidence": r.confidence,
                "trend": r.trend.value,
            })
        print(json.dumps(out, ensure_ascii=False))

    else:
        print(json.dumps({"error": "Unknown price-predict subcommand"}, ensure_ascii=False))

    return True


# ─── Image Comparison ───

def _add_image_comparison_parsers(subparsers) -> None:
    """Add image-compare subparsers."""
    ic = subparsers.add_parser("image-compare", help="Product image comparison (perceptual hashing)")
    ics = ic.add_subparsers(dest="ic_command")

    # hash
    p = ics.add_parser("hash", help="Compute perceptual hash of an image")
    p.add_argument("--pixels", required=True, nargs="+", type=int, help="Grayscale pixel values (64 for 8x8)")
    p.add_argument("--width", type=int, default=8)
    p.add_argument("--height", type=int, default=8)
    p.add_argument("--algorithm", choices=["ahash", "dhash", "phash"], default="ahash")

    # compare
    p = ics.add_parser("compare", help="Compare two images")
    p.add_argument("--source", required=True, nargs="+", type=int, help="Source pixels")
    p.add_argument("--target", required=True, nargs="+", type=int, help="Target pixels")
    p.add_argument("--algorithm", choices=["ahash", "dhash", "phash"], default="ahash")
    p.add_argument("--threshold", type=float, default=0.85, help="Duplicate threshold")


def _run_image_compare(args) -> bool:
    """Execute image-compare CLI command."""
    cmd = getattr(args, "ic_command", None)
    algo_map = {
        "ahash": HashAlgorithm.AHASH,
        "dhash": HashAlgorithm.DHASH,
        "phash": HashAlgorithm.PHASH,
    }

    if cmd == "hash":
        from aios_core.image_comparison import (
            average_hash,
            difference_hash,
            perceptual_hash,
        )
        pixels = getattr(args, "pixels", [])
        w = getattr(args, "width", 8)
        h = getattr(args, "height", 8)
        algo = algo_map.get(getattr(args, "algorithm", "ahash"), HashAlgorithm.AHASH)

        if algo == HashAlgorithm.AHASH:
            result = average_hash(pixels, w, h)
        elif algo == HashAlgorithm.DHASH:
            result = difference_hash(pixels, w, h)
        else:
            result = perceptual_hash(pixels, w, h)

        out = {
            "algorithm": result.algorithm.value,
            "hash_value": result.hash_value,
            "bit_string": result.bit_string[:16] + "...",
            "width": result.width,
            "height": result.height,
        }
        print(json.dumps(out, ensure_ascii=False))

    elif cmd == "compare":
        src = getattr(args, "source", [])
        tgt = getattr(args, "target", [])
        threshold = getattr(args, "threshold", 0.85)
        algo = algo_map.get(getattr(args, "algorithm", "ahash"), HashAlgorithm.AHASH)

        engine = ImageComparisonEngine(
            hash_algorithm=algo, duplicate_threshold=threshold
        )
        result = engine.compare(
            src, 8, 8, tgt, 8, 8, algorithm=algo
        )
        out = {
            "hash_similarity": result.hash_similarity,
            "composite_similarity": result.composite_similarity,
            "is_duplicate": result.is_duplicate,
            "hash_distance": result.hash_distance,
            "algorithm": result.algorithm.value,
        }
        print(json.dumps(out, ensure_ascii=False))

    else:
        print(json.dumps({"error": "Unknown image-compare subcommand"}, ensure_ascii=False))

    return True


# ─── Fleet Scheduler ───

def _add_fleet_parsers(subparsers) -> None:
    """Add fleet-scheduler subparsers."""
    fl = subparsers.add_parser("fleet", help="Multi-device fleet scheduler")
    fls = fl.add_subparsers(dest="fleet_command")

    # stats
    fls.add_parser("stats", help="Show fleet statistics")

    # schedule
    p = fls.add_parser("schedule", help="Schedule a task on fleet")
    p.add_argument("--platform", required=True, help="Target platform")
    p.add_argument("--action", required=True, help="Task action (collect, parse, monitor)")
    p.add_argument("--priority", choices=["critical", "high", "normal", "low"], default="normal")

    # register
    p = fls.add_parser("register", help="Register a device in fleet")
    p.add_argument("--device-id", required=True)
    p.add_argument("--platform", default="")
    p.add_argument("--max-concurrent", type=int, default=1)

    # complete
    p = fls.add_parser("complete", help="Complete a task")
    p.add_argument("--task-id", required=True)

    # health
    fls.add_parser("health", help="Run fleet health check")


def _run_fleet(args) -> bool:
    """Execute fleet CLI command."""
    cmd = getattr(args, "fleet_command", None)

    # Use a shared scheduler instance (stored in args or singleton)
    scheduler = getattr(args, "_fleet_scheduler", None)
    if scheduler is None:
        scheduler = FleetScheduler(policy=SchedulingPolicy.LEAST_BUSY)
        args._fleet_scheduler = scheduler

    if cmd == "stats":
        stats = scheduler.stats()
        print(json.dumps(stats, ensure_ascii=False))

    elif cmd == "schedule":
        priority_map = {
            "critical": TaskPriority.CRITICAL,
            "high": TaskPriority.HIGH,
            "normal": TaskPriority.NORMAL,
            "low": TaskPriority.LOW,
        }
        platform = getattr(args, "platform", "olx")
        action = getattr(args, "action", "collect")
        priority = priority_map.get(getattr(args, "priority", "normal"), TaskPriority.NORMAL)

        task = scheduler.schedule(platform, action, priority)
        if task:
            out = {
                "task_id": task.task_id,
                "status": task.status.value,
                "assigned_device": task.assigned_device,
                "priority": task.priority.value,
            }
        else:
            out = {"error": "No available device"}
        print(json.dumps(out, ensure_ascii=False))

    elif cmd == "register":
        device_id = getattr(args, "device_id", "dev1")
        platform = getattr(args, "platform", "")
        max_conc = getattr(args, "max_concurrent", 1)

        dev = FleetDevice(
            device_id=device_id,
            platform=platform,
            max_concurrent=max_conc,
        )
        scheduler.register_device(dev)
        print(json.dumps({"registered": device_id, "platform": platform}, ensure_ascii=False))

    elif cmd == "complete":
        task_id = getattr(args, "task_id", "")
        result = scheduler.complete_task(task_id)
        out = {"task_id": task_id, "status": result.status.value} if result else {"error": "Task not found"}
        print(json.dumps(out, ensure_ascii=False))

    elif cmd == "health":
        health = scheduler.health_check()
        out = {dev_id: status.value for dev_id, status in health.items()}
        print(json.dumps(out, ensure_ascii=False))

    else:
        print(json.dumps({"error": "Unknown fleet subcommand"}, ensure_ascii=False))

    return True
