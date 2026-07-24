#!/usr/bin/env python3
"""AIOS CLI — Rozetka.ua marketplace commands."""

import argparse
import json


def _add_rozetka_parsers(subparsers) -> None:
    """Register the ``rozetka`` subcommand tree."""
    rz = subparsers.add_parser("rozetka", help="Rozetka.ua marketplace commands")
    rz_sub = rz.add_subparsers(dest="rozetka_command")

    def with_db(p):
        """Add ``--db`` and ``--profile`` arguments."""
        p.add_argument("--db", default=None, help="SQLite database file")
        p.add_argument("--profile", default=None, help="Profile name from registry")

    stats = rz_sub.add_parser("stats", help="Product statistics")
    stats.add_argument("--query", default=None)
    with_db(stats)

    chats = rz_sub.add_parser("chats", help="List seller chat threads")
    with_db(chats)

    dm_send = rz_sub.add_parser("dm-send", help="Queue a seller chat reply")
    dm_send.add_argument("--chat", required=True, help="Chat key (e.g. chat:seller)")
    dm_send.add_argument("--text", required=True, help="Reply text")
    dm_send.add_argument("--auto-send", action="store_true", help="Send immediately (default: queue)")
    with_db(dm_send)

    dm_flush = rz_sub.add_parser("dm-flush", help="Flush pending outbox replies")
    with_db(dm_flush)

    dm_outbox = rz_sub.add_parser("dm-outbox", help="List pending reply drafts")
    with_db(dm_outbox)

    rz_sub.add_parser("doctor", help="Environment readiness checklist")


def _resolve_rozetka_db(args) -> str:
    """Resolve DB path for rozetka command."""
    from aios_core.platforms import Profile, resolve_profile

    if getattr(args, "db", None):
        return args.db
    profile = resolve_profile("rozetka", getattr(args, "profile", None))
    return profile.db_path


def _run_rozetka(args) -> bool:
    """Dispatch a Rozetka subcommand.

    Returns True if the command was recognized and executed, False otherwise.
    """
    from aios_core.modules.rozetka import RozetkaStorage

    if args.rozetka_command == "stats":
        with RozetkaStorage(_resolve_rozetka_db(args)) as storage:
            ads = storage.get_ads(query=args.query)
            print(json.dumps({
                "total_ads": len(ads),
                "query": args.query,
            }, ensure_ascii=False, indent=2))
        return True

    if args.rozetka_command == "chats":
        with RozetkaStorage(_resolve_rozetka_db(args)) as storage:
            threads = storage.outbox_list()
            print(json.dumps(threads, ensure_ascii=False, indent=2))
        return True

    if args.rozetka_command == "dm-send":
        with RozetkaStorage(_resolve_rozetka_db(args)) as storage:
            from aios_core.modules.rozetka import RozetkaMessenger
            messenger = RozetkaMessenger(storage=storage)
            result = messenger.send_reply(args.chat, args.text)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return True

    if args.rozetka_command == "dm-flush":
        with RozetkaStorage(_resolve_rozetka_db(args)) as storage:
            from aios_core.modules.rozetka import RozetkaMessenger
            messenger = RozetkaMessenger(storage=storage)
            flushed = messenger.flush_outbox()
            print(json.dumps(flushed, ensure_ascii=False, indent=2))
        return True

    if args.rozetka_command == "dm-outbox":
        with RozetkaStorage(_resolve_rozetka_db(args)) as storage:
            print(json.dumps(storage.outbox_list(), ensure_ascii=False, indent=2))
        return True

    if args.rozetka_command == "doctor":
        from aios_core.modules.rozetka import RozetkaBootstrap
        report = RozetkaBootstrap().doctor()
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return True

    return False
