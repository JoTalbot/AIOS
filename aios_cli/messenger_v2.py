#!/usr/bin/env python3
"""AIOS CLI — WhatsApp/Viber messenger commands."""

import argparse
import json


def _add_messenger_v2_parsers(subparsers) -> None:
    """Register enhanced WhatsApp/Viber subcommands."""
    # WhatsApp v2
    wa = subparsers.add_parser("whatsapp-v2", help="WhatsApp enhanced commands")
    wa_sub = wa.add_subparsers(dest="wa_v2_command")

    def with_db(p):
        p.add_argument("--db", default=None)

    wa_sub.add_parser("doctor", help="Environment readiness")

    # Contacts
    ct = wa_sub.add_parser("contacts", help="Contact management")
    ct_sub = ct.add_subparsers(dest="contacts_command")
    p = ct_sub.add_parser("list", help="List contacts")
    p.add_argument("--tag", default=None)
    with_db(p)
    p = ct_sub.add_parser("tag", help="Tag a contact")
    p.add_argument("--jid", required=True)
    p.add_argument("--tag", required=True)
    with_db(p)

    # Broadcast
    bc = wa_sub.add_parser("broadcast", help="Broadcast scheduler")
    bc_sub = bc.add_subparsers(dest="broadcast_command")
    p = bc_sub.add_parser("create", help="Create broadcast")
    p.add_argument("--text", required=True)
    p.add_argument("--tags", nargs="+", default=[])
    with_db(p)
    p = bc_sub.add_parser("approve", help="Approve broadcast")
    p.add_argument("--id", required=True)
    with_db(p)
    p = bc_sub.add_parser("list", help="List broadcasts")
    p.add_argument("--status", default=None, choices=["draft", "approved", "completed", "failed"])
    with_db(p)

    # Analytics
    wa_sub.add_parser("analytics", help="Chat analytics")

    # Viber v2
    vi = subparsers.add_parser("viber-v2", help="Viber enhanced commands")
    vi_sub = vi.add_subparsers(dest="vi_v2_command")

    vi_sub.add_parser("doctor", help="Environment readiness")

    ct = vi_sub.add_parser("contacts", help="Contact management")
    ct_sub = ct.add_subparsers(dest="contacts_command")
    p = ct_sub.add_parser("list", help="List contacts")
    p.add_argument("--tag", default=None)
    p.add_argument("--db", default=None)

    vi_sub.add_parser("analytics", help="Chat analytics")


def _run_whatsapp_v2(args) -> bool:
    """Dispatch WhatsApp v2 subcommand."""
    from aios_core.modules.whatsapp import WhatsAppStorage, ContactManager, BroadcastScheduler, ChatAnalyzer

    db = getattr(args, "db", None) or ":memory:"
    storage = WhatsAppStorage(db)

    if args.wa_v2_command == "doctor":
        from aios_core.modules.whatsapp import WhatsAppBootstrap
        report = WhatsAppBootstrap().doctor()
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return True

    if args.wa_v2_command == "contacts":
        manager = ContactManager(storage)
        if args.contacts_command == "list":
            contacts = manager.list_contacts(tag=args.tag)
            print(json.dumps([c.to_dict() for c in contacts], ensure_ascii=False, indent=2))
        elif args.contacts_command == "tag":
            manager.tag_contact(args.jid, args.tag)
            print(json.dumps({"tagged": True, "jid": args.jid, "tag": args.tag}, indent=2))
        return True

    if args.wa_v2_command == "broadcast":
        scheduler = BroadcastScheduler(storage)
        if args.broadcast_command == "create":
            msg = scheduler.create_broadcast(args.text, contact_tags=args.tags)
            print(json.dumps(msg.to_dict(), indent=2))
        elif args.broadcast_command == "approve":
            approved = scheduler.approve_broadcast(args.id)
            print(json.dumps(approved.to_dict() if approved else {"error": "not found"}, indent=2))
        elif args.broadcast_command == "list":
            status = None
            if args.status:
                from aios_core.modules.whatsapp.broadcast_scheduler import BroadcastStatus
                status = BroadcastStatus(args.status)
            broadcasts = scheduler.list_broadcasts(status=status)
            print(json.dumps([b.to_dict() for b in broadcasts], indent=2))
        return True

    if args.wa_v2_command == "analytics":
        analyzer = ChatAnalyzer(storage, platform="whatsapp")
        analytics = analyzer.analytics()
        sentiment = analyzer.sentiment_summary()
        print(json.dumps({"analytics": analytics.to_dict(), "sentiment": sentiment}, indent=2))
        return True

    return False


def _run_viber_v2(args) -> bool:
    """Dispatch Viber v2 subcommand."""
    from aios_core.modules.viber import ViberStorage, ViberContactManager, ViberChatAnalyzer

    db = getattr(args, "db", None) or ":memory:"
    storage = ViberStorage(db)

    if args.vi_v2_command == "doctor":
        from aios_core.modules.viber import ViberBootstrap
        report = ViberBootstrap().doctor()
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return True

    if args.vi_v2_command == "contacts":
        manager = ViberContactManager(storage)
        contacts = manager.list_contacts(tag=args.tag)
        print(json.dumps([c.to_dict() for c in contacts], ensure_ascii=False, indent=2))
        return True

    if args.vi_v2_command == "analytics":
        analyzer = ViberChatAnalyzer(storage)
        analytics = analyzer.analytics()
        print(json.dumps(analytics.to_dict(), indent=2))
        return True

    return False
