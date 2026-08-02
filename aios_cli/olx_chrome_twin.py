"""CLI for OLX Chrome Twin adapter"""
import json, asyncio
from pathlib import Path

def run_olx_chrome_twin(args):
    cmd = getattr(args, "olx_chrome_twin_command", None) or "doctor"
    try:
        from aios_core.platforms.olx_chrome_twin_adapter import OLXChromeTwinAdapter

        async def doctor():
            adapter = OLXChromeTwinAdapter(config={"olx_login": args.login, "profile": args.profile})
            healthy = await adapter.health_check()
            return {"healthy": healthy, "login": args.login, "profile": args.profile, "google_account": "jo.talbot@gmail.com"}

        async def login():
            adapter = OLXChromeTwinAdapter(config={"olx_login": args.login, "profile": args.profile})
            result = await adapter.login_to_olx(use_google=args.use_google)
            await adapter.close()
            return result

        async def my_ads():
            adapter = OLXChromeTwinAdapter(config={"olx_login": args.login, "profile": args.profile})
            await adapter.login_to_olx(use_google=args.use_google)
            ads = await adapter.collect_my_ads()
            await adapter.close()
            return {"count": len(ads), "ads": ads[:10]}

        async def create_ad():
            adapter = OLXChromeTwinAdapter(config={"olx_login": args.login, "profile": args.profile})
            await adapter.login_to_olx(use_google=args.use_google)
            result = await adapter.create_ad(title=args.title, description=args.desc, price=args.price)
            await adapter.close()
            return result

        if cmd == "doctor":
            result = asyncio.run(doctor())
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return True
        elif cmd == "login":
            result = asyncio.run(login())
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return True
        elif cmd == "my_ads":
            result = asyncio.run(my_ads())
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return True
        elif cmd == "create_ad":
            result = asyncio.run(create_ad())
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return True

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="OLX Chrome Twin - via Google account and saved passwords")
    parser.add_argument("--login", default="959052288", help="OLX login phone")
    parser.add_argument("--profile", default="default", help="Chrome Twin profile")
    parser.add_argument("--use-google", action="store_true", default=True, help="Use Google login first")
    parser.add_argument("--title", default="", help="Ad title")
    parser.add_argument("--desc", default="", help="Ad description")
    parser.add_argument("--price", default="", help="Ad price")
    parser.add_argument("olx_chrome_twin_command", nargs="?", default="doctor", help="Command: doctor, login, my_ads, create_ad")
    args = parser.parse_args()
    run_olx_chrome_twin(args)
