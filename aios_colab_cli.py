#!/usr/bin/env python3
"""
AIOS Colab Farm - Единый CLI управления фермой (улучшение)

Управление всеми компонентами Colab-фермы из одной команды:
  - сервисы (реестр), ноды, задачи, heartbeat
  - сбор рыночных данных, ML-инференс, RAG-индекс
  - скрапинг, модели, датасеты

Использование:
    python aios_colab_cli.py status
    python aios_colab_cli.py services list
    python aios_colab_cli.py nodes list
    python aios_colab_cli.py jobs list
    python aios_colab_cli.py data collect --symbols BTC ETH
    python aios_colab_cli.py ml signal
    python aios_colab_cli.py rag search "как регистрировать сервис"
    python aios_colab_cli.py rag build
    python aios_colab_cli.py models import --src <path>
    python aios_colab_cli.py docs
"""

from __future__ import annotations

import sys
import json
import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))


# ------------------------------------------------------------- helpers ------
def _print(obj) -> None:
    if isinstance(obj, str):
        print(obj)
    else:
        print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


# ------------------------------------------------------------- services ------
def cmd_services_list():
    from aios_core.colab.colab_registry import colab_registry
    _print(colab_registry.summary())


def cmd_services_health(name):
    from aios_core.colab.colab_registry import colab_registry
    _print(colab_registry.health_check(name))


def cmd_services_register(kind, url, model, name, node):
    from aios_core.colab.colab_registry import colab_registry
    _print(colab_registry.register(kind=kind, base_url=url, model=model, name=name, node_id=node))


# ------------------------------------------------------------- nodes ---------
def cmd_nodes_list():
    from aios_core.colab.cluster import colab_cluster
    _print({"summary": colab_cluster.summary(), "nodes": colab_cluster.list_nodes()})


# ------------------------------------------------------------- jobs ---------
def cmd_jobs_list(status):
    from aios_core.colab.scheduler import colab_scheduler
    _print(colab_scheduler.list_tasks(status=status))


def cmd_jobs_run():
    from aios_core.colab.scheduler import colab_scheduler
    _print(colab_scheduler.run_pending())


# ------------------------------------------------------------- data ---------
def cmd_data_collect(symbols, tf, limit, exchanges):
    from aios_core.quant.data_collector import MarketDataCollector
    c = MarketDataCollector(symbols=symbols, exchanges=exchanges)
    _print(c.collect_ohlcv_all(timeframe=tf, limit=limit))


def cmd_data_export():
    from aios_core.quant.data_collector import MarketDataCollector
    c = MarketDataCollector()
    _print({"archive": c.export_for_colab()})


# ------------------------------------------------------------- ml -----------
def cmd_ml_signal():
    from aios_core.quant.ml_predictor import QuantMLPredictor
    _print(QuantMLPredictor().signal_json())


# ------------------------------------------------------------- rag ----------
def cmd_rag_search(query, n):
    from aios_core.rag.embeddings_store import EmbeddingsStore
    store = EmbeddingsStore()
    print(f"В коллекции: {store.count()} чанков")
    _print(store.search(query, n_results=n))


def cmd_rag_build():
    from aios_core.rag.index_builder import build_corpus
    build_corpus()


# ------------------------------------------------------------- models -------
def cmd_models_import(src, extract):
    from scripts.import_colab_models import main as imp
    sys.argv = ["import_colab_models", "--src", str(src)] + (["--extract"] if extract else [])
    imp()


# ------------------------------------------------------------- overview -----
def cmd_status():
    from aios_core.colab.colab_registry import colab_registry
    from aios_core.colab.cluster import colab_cluster
    from aios_core.colab.scheduler import colab_scheduler
    from aios_core.rag.embeddings_store import EmbeddingsStore
    from aios_core.quant.ml_predictor import QuantMLPredictor
    from pathlib import Path
    import subprocess

    status = {
        "services": colab_registry.count_by_kind(),
        "total_services": len(colab_registry.all()),
        "nodes": colab_cluster.summary(),
        "tasks_pending": len(colab_scheduler.pending()),
        "rag_chunks": EmbeddingsStore().count(),
        "quant_ml_model": QuantMLPredictor().available,
        "signals_file": (REPO_ROOT / "data/quant/ml_signals.json").exists(),
        "market_data_dirs": len([d for d in (REPO_ROOT / "data/quant").iterdir() if d.is_dir() and d.name not in ("export", "models", "uniswap_v3")]) if (REPO_ROOT / "data/quant").exists() else 0,
    }
    _print(status)


# ------------------------------------------------------------- main ---------
def main() -> int:
    ap = argparse.ArgumentParser(description="AIOS Colab Farm CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status")

    s = sub.add_parser("services")
    ssub = s.add_subparsers(dest="action", required=True)
    ssub.add_parser("list")
    ph = ssub.add_parser("health"); ph.add_argument("name")
    pr = ssub.add_parser("register"); pr.add_argument("kind"); pr.add_argument("url")
    pr.add_argument("--model"); pr.add_argument("--name"); pr.add_argument("--node", default="local")

    n = sub.add_parser("nodes")
    n.add_argument("action", choices=["list"])

    j = sub.add_parser("jobs")
    jsub = j.add_subparsers(dest="action", required=True)
    pjl = jsub.add_parser("list"); pjl.add_argument("--status")
    jsub.add_parser("run")

    d = sub.add_parser("data")
    dsub = d.add_subparsers(dest="action", required=True)
    pc = dsub.add_parser("collect"); pc.add_argument("--symbols", nargs="*"); pc.add_argument("--tf", default="1h"); pc.add_argument("--limit", type=int, default=500); pc.add_argument("--exchanges", nargs="*")
    dsub.add_parser("export")

    ml = sub.add_parser("ml")
    mlsub = ml.add_subparsers(dest="action", required=True)
    mlsub.add_parser("signal")

    rg = sub.add_parser("rag")
    rgsub = rg.add_subparsers(dest="action", required=True)
    ps = rgsub.add_parser("search"); ps.add_argument("query"); ps.add_argument("--n", type=int, default=5)
    rgsub.add_parser("build")

    mo = sub.add_parser("models")
    mosub = mo.add_subparsers(dest="action", required=True)
    pmi = mosub.add_parser("import"); pmi.add_argument("--src", required=True); pmi.add_argument("--extract", action="store_true")

    args = ap.parse_args()

    if args.cmd == "status": cmd_status()
    elif args.cmd == "services":
        if args.action == "list": cmd_services_list()
        elif args.action == "health": cmd_services_health(args.name)
        elif args.action == "register": cmd_services_register(args.kind, args.url, args.model, args.name, args.node)
    elif args.cmd == "nodes": cmd_nodes_list()
    elif args.cmd == "jobs":
        if args.action == "list": cmd_jobs_list(args.status)
        else: cmd_jobs_run()
    elif args.cmd == "data":
        if args.action == "collect": cmd_data_collect(args.symbols, args.tf, args.limit, args.exchanges)
        else: cmd_data_export()
    elif args.cmd == "ml": cmd_ml_signal()
    elif args.cmd == "rag":
        if args.action == "search": cmd_rag_search(args.query, args.n)
        else: cmd_rag_build()
    elif args.cmd == "models": cmd_models_import(args.src, args.extract)
    return 0


if __name__ == "__main__":
    sys.exit(main())
