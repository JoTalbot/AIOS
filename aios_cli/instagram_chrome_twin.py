"""CLI for Instagram Chrome Twin adapter."""
import json
import asyncio
import sys
from pathlib import Path

# корень проекта в sys.path (для запуска как скрипта)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def run_instagram_chrome_twin(args):
    cmd = getattr(args, "instagram_chrome_twin_command", None) or "doctor"
    try:
        from aios_core.platforms.instagram_chrome_twin_adapter import InstagramChromeTwinAdapter

        async def doctor():
            adapter = InstagramChromeTwinAdapter(config={"profile": args.profile})
            healthy = await adapter.health_check()
            login = await adapter.check_login()
            await adapter.close()
            return {"healthy": healthy, "login": login, "profile": args.profile}

        async def profile():
            adapter = InstagramChromeTwinAdapter(config={"profile": args.profile})
            info = await adapter.get_profile_info(username=args.username)
            await adapter.close()
            return info

        async def my_posts():
            adapter = InstagramChromeTwinAdapter(config={"profile": args.profile})
            posts = await adapter.get_my_posts(limit=args.limit)
            await adapter.close()
            return {"count": len(posts), "posts": posts}

        async def post():
            adapter = InstagramChromeTwinAdapter(config={"profile": args.profile})
            info = await adapter.get_post_details(args.code)
            await adapter.close()
            return info

        if cmd == "doctor":
            result = asyncio.run(doctor())
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return True
        elif cmd == "profile":
            result = asyncio.run(profile())
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return True
        elif cmd == "my_posts":
            result = asyncio.run(my_posts())
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return True
        elif cmd == "post":
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
    parser = argparse.ArgumentParser(description="Instagram Chrome Twin - через залогиненную сессию в профиле Chrome Twin")
    parser.add_argument("--profile", default="default", help="Chrome Twin profile")
    parser.add_argument("--username", default=None, help="Instagram username (для profile)")
    parser.add_argument("--limit", type=int, default=10, help="Лимит постов (my_posts)")
    parser.add_argument("--code", default="", help="Код поста Instagram (post)")
    parser.add_argument("instagram_chrome_twin_command", nargs="?", default="doctor",
                        help="Command: doctor, profile, my_posts, post")
    args = parser.parse_args()
    run_instagram_chrome_twin(args)
