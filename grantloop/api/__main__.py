"""`python -m grantloop.api` — dashboard and live read API on one port."""

from __future__ import annotations

import argparse
import os

from .server import serve


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="grantloop.api", description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8080")))
    parser.add_argument("--dlq", metavar="TXN_ID",
                        help="force this transaction to fail, populating the DLQ panel")
    args = parser.parse_args(argv)
    serve(args.host, args.port, fail_txn=args.dlq)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
