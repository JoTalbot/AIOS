"""CLI for Chrome Twin adapter"""
import json, asyncio
from pathlib import Path

def run_chrome_twin(args):
    cmd = getattr(args, "chrome_twin_command", None) or "doctor"
    try:
        from aios_core.platforms.chrome_twin_adapter import ChromeTwinAdapter

        async def doctor():
            adapter = ChromeTwinAdapter(config={"profile": args.profile, "user_data_dir": args.data_dir, "headless": args.headless})
            healthy = await adapter.health_check()
            return {"healthy": healthy, "profile": args.profile, "data_dir": args.data_dir, "has_playwright": True}

        async def navigate():
            adapter = ChromeTwinAdapter(config={"profile": args.profile, "user_data_dir": args.data_dir, "headless": args.headless})
            result = await adapter.navigate(args.url)
            await adapter.close()
            return result

        async def gmail_send():
            adapter = ChromeTwinAdapter(config={"profile": args.profile, "user_data_dir": args.data_dir})
            result = await adapter.execute_google_action("gmail", "send", {"to": args.to, "subject": args.subject, "body": args.body, "confirm": args.confirm})
            await adapter.close()
            return result

        async def custom():
            adapter = ChromeTwinAdapter(config={"profile": args.profile, "user_data_dir": args.data_dir})
            result = await adapter.execute_custom_action(args.instruction)
            await adapter.close()
            return result

        async def screenshot():
            adapter = ChromeTwinAdapter(config={"profile": args.profile, "user_data_dir": args.data_dir})
            path = await adapter.screenshot(args.output)
            await adapter.close()
            return {"screenshot": path}

        if cmd == "doctor":
            result = asyncio.run(doctor())
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return True
        elif cmd == "navigate":
            result = asyncio.run(navigate())
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return True
        elif cmd == "gmail_send":
            result = asyncio.run(gmail_send())
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return True
        elif cmd == "custom":
            result = asyncio.run(custom())
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return True
        elif cmd == "screenshot":
            result = asyncio.run(screenshot())
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return True

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Chrome Twin - Двойник пользователя в Chrome")
    parser.add_argument("--profile", default="default", help="Chrome profile name")
    parser.add_argument("--data-dir", default="data/chrome_twin/default", help="User data dir")
    parser.add_argument("--headless", action="store_true", help="Run headless")
    parser.add_argument("--url", default="https://www.google.com", help="URL to navigate")
    parser.add_argument("--to", default="", help="Email to")
    parser.add_argument("--subject", default="", help="Email subject")
    parser.add_argument("--body", default="", help="Email body")
    parser.add_argument("--instruction", default="", help="Custom instruction")
    parser.add_argument("--output", default=None, help="Screenshot output path")
    parser.add_argument("--confirm", action="store_true", help="Confirm action (e.g., actually send email)")
    parser.add_argument("chrome_twin_command", nargs="?", default="doctor", help="Command: doctor, navigate, gmail_send, custom, screenshot")
    args = parser.parse_args()
    run_chrome_twin(args)
