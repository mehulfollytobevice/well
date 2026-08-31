"""CLI entrypoint for WellGround."""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="wellground", description="WellGround ForgeOps agent")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("serve", help="Start the FastAPI server")
    sub.add_parser("version", help="Print package version")

    args = parser.parse_args(argv)

    if args.command == "version" or args.command is None:
        from wellground import __version__

        print(__version__)
        return

    if args.command == "serve":
        import os

        import uvicorn

        port = int(os.environ.get("PORT", "8000"))
        uvicorn.run(
            "wellground.api.app:app",
            host="0.0.0.0",
            port=port,
            reload=os.environ.get("WELLGROUND_ENV", "development") == "development",
        )
        return

    parser.print_help()


if __name__ == "__main__":
    main()
