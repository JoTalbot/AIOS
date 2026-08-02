"""AIOS CLI — Instagram Emulator commands"""
import json
from pathlib import Path

def _lazy_import(module_path: str, attr: str = None):
    import importlib
    mod = importlib.import_module(module_path)
    return getattr(mod, attr) if attr else mod

def _run_instagram_emulator(args) -> bool:
    """Instagram Emulator: doctor / collect / reels / Direct / post / login"""
    cmd = getattr(args, "instagram_emulator_command", None) or "doctor"
    try:
        if cmd == "doctor":
            from aios_core.platforms.instagram_emulator_adapter import InstagramEmulatorAdapter
            import asyncio
            async def doctor():
                adapter = InstagramEmulatorAdapter(config={"serial": args.serial, "profile": args.profile})
                healthy = await adapter.health_check()
                return {"healthy": healthy, "serial": args.serial, "profile": args.profile, "package": "com.instagram.android"}
            import asyncio
            report = asyncio.run(doctor())
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return True

        if cmd == "login":
            from aios_core.platforms.instagram_emulator_adapter import InstagramEmulatorAdapter
            import asyncio
            async def login():
                adapter = InstagramEmulatorAdapter(config={"serial": args.serial, "profile": args.profile})
                return await adapter.login()
            result = asyncio.run(login())
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return True

        if cmd == "collect":
            from aios_core.platforms.instagram_emulator_adapter import InstagramEmulatorAdapter
            import asyncio
            async def collect():
                adapter = InstagramEmulatorAdapter(config={"serial": args.serial, "profile": args.profile})
                return await adapter.collect_feed(max_cards=args.max, query=args.query)
            cards = asyncio.run(collect())
            print(json.dumps({"count": len(cards), "cards": cards[:5]}, ensure_ascii=False, indent=2))
            return True

        if cmd == "reels":
            from aios_core.platforms.instagram_emulator_adapter import InstagramEmulatorAdapter
            import asyncio
            async def reels():
                adapter = InstagramEmulatorAdapter(config={"serial": args.serial, "profile": args.profile})
                return await adapter.collect_reels(max_cards=args.max)
            cards = asyncio.run(reels())
            print(json.dumps({"count": len(cards), "cards": cards[:5]}, ensure_ascii=False, indent=2))
            return True

        if cmd == "send":
            from aios_core.platforms.instagram_emulator_adapter import InstagramEmulatorAdapter
            import asyncio
            async def send():
                adapter = InstagramEmulatorAdapter(config={"serial": args.serial, "profile": args.profile})
                return await adapter.send_message(args.recipient, args.text, metadata={"auto_send": args.confirm})
            result = asyncio.run(send())
            print(json.dumps({"message_id": result.message_id, "recipient": result.recipient_id}, ensure_ascii=False, indent=2))
            return True

        if cmd == "post":
            from aios_core.platforms.instagram_emulator_adapter import InstagramEmulatorAdapter
            import asyncio
            async def post():
                adapter = InstagramEmulatorAdapter(config={"serial": args.serial, "profile": args.profile})
                return await adapter.create_post(caption=args.caption, image_path=args.image)
            result = asyncio.run(post())
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return True

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Instagram Emulator CLI")
    parser.add_argument("--serial", default="emulator-5554", help="ADB serial")
    parser.add_argument("--profile", default="default", help="Profile name")
    parser.add_argument("--max", type=int, default=20, help="Max cards")
    parser.add_argument("--query", default=None, help="Search query")
    parser.add_argument("--recipient", default="", help="Recipient ID for send")
    parser.add_argument("--text", default="", help="Text to send")
    parser.add_argument("--caption", default="", help="Post caption")
    parser.add_argument("--image", default=None, help="Image path for post")
    parser.add_argument("--confirm", action="store_true", help="Confirm auto-send")
    parser.add_argument("instagram_emulator_command", nargs="?", default="doctor", help="Command: doctor, login, collect, reels, send, post")
    args = parser.parse_args()
    _run_instagram_emulator(args)
