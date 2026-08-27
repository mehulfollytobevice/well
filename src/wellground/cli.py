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
        print("Serve is not implemented yet. See the roadmap in README.md.", file=sys.stderr)
        raise SystemExit(1)

    parser.print_help()


if __name__ == "__main__":
    main()
