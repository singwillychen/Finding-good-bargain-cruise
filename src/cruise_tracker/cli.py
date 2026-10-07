import argparse
import logging

from .config import get_settings
from .db import init_db, session_scope
from .seed import seed_reference


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    p = argparse.ArgumentParser(prog="cruise", description="Cruise bargain tracker")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init-db", help="create tables and seed ports/regions/cruise lines")
    sc = sub.add_parser("scrape", help="run the daily job now")
    sc.add_argument("--source", action="append", help="vtg, cruisedirect or demo (default: SOURCES)")
    sub.add_parser("score", help="recompute deal scores")
    dg = sub.add_parser("digest", help="build the weekly Telegram digest")
    dg.add_argument("--send", action="store_true", help="actually send it (default: print only)")
    sub.add_parser("telegram-chat-id", help="list chats that have messaged your bot")
    sv = sub.add_parser("serve", help="web UI + scheduler")
    sv.add_argument("--host", default="0.0.0.0")
    sv.add_argument("--port", type=int, default=8000)
    sv.add_argument("--no-scheduler", action="store_true")
    args = p.parse_args(argv)

    init_db()
    with session_scope() as s:
        seed_reference(s)

    if args.cmd == "init-db":
        print(f"database ready at {get_settings().db_url}")
    elif args.cmd == "scrape":
        from .pipeline import daily_job

        daily_job(args.source)
    elif args.cmd == "score":
        from .scoring import compute_deals

        with session_scope() as s:
            print(f"scored {len(compute_deals(s))} sailings")
    elif args.cmd == "digest":
        from .notify.digest import send_digest

        with session_scope() as s:
            print(send_digest(s, dry_run=not args.send))
    elif args.cmd == "telegram-chat-id":
        from .notify.telegram import find_chat_ids

        for chat_id, name in find_chat_ids(get_settings().telegram_bot_token):
            print(chat_id, name)
    elif args.cmd == "serve":
        import uvicorn

        from .web.app import create_app

        uvicorn.run(create_app(scheduler=not args.no_scheduler), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
