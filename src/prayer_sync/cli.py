from __future__ import annotations

import argparse
import logging
import sys

from . import service
from .observability import configure_logging, log_event

log = logging.getLogger("prayer_sync")


def cmd_fetch(config_path: str) -> int:
    result = service.run_fetch(config_path)
    if result.ok:
        log_event(log, logging.INFO, "fetch.completed", outcome="success")
        return 0
    log_event(log, logging.ERROR, "fetch.completed", outcome="failure")
    return 1


def cmd_sync(config_path: str) -> int:
    result = service.run_sync(config_path)
    if result.ok:
        log_event(log, logging.INFO, "sync.completed", outcome="success")
        return 0
    log_event(log, logging.ERROR, "sync.completed", outcome="failure")
    return 1


def cmd_serve(config_path: str, host: str, port: int) -> int:
    import uvicorn

    from . import scheduler as scheduler_module
    from .api import create_app

    app = create_app(config_path)
    scheduler_module.start(config_path)
    try:
        uvicorn.run(app, host=host, port=port, log_config=None, access_log=False)
    finally:
        scheduler_module.shutdown()
    return 0


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    config_parent = argparse.ArgumentParser(add_help=False)
    config_parent.add_argument(
        "-c", "--config", default="config.yaml", help="path to config.yaml"
    )

    parser = argparse.ArgumentParser(prog="yaad", parents=[config_parent])
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser(
        "fetch", parents=[config_parent], help="fetch today's prayer times from the configured provider"
    )
    subparsers.add_parser(
        "sync", parents=[config_parent], help="sync today's prayer times to iCloud"
    )
    serve_parser = subparsers.add_parser(
        "serve",
        parents=[config_parent],
        help="run the API + web UI + daily scheduler",
    )
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8000)

    args = parser.parse_args(argv)

    if args.command == "fetch":
        return cmd_fetch(args.config)
    if args.command == "sync":
        return cmd_sync(args.config)
    if args.command == "serve":
        return cmd_serve(args.config, args.host, args.port)

    parser.error(f"unknown command {args.command!r}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
