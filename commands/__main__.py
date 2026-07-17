"""``python -m commands`` entry point.

Usage:
    python -m commands <command> [args] --out <out_dir>
"""
from __future__ import annotations

import sys

from commands.dispatcher import dispatch, GateBlocked


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python -m commands <new|review|compliance> [--out DIR] [--force]",
              file=sys.stderr)
        return 1

    cmd = sys.argv[1]
    args = sys.argv[2:]

    # Extract --out from args
    out_dir = "./out"
    for i, a in enumerate(args):
        if a == "--out" and i + 1 < len(args):
            out_dir = args[i + 1]
            break

    try:
        result = dispatch(cmd, args, out_dir)
    except GateBlocked as e:
        print(f"⛔ {e}", file=sys.stderr)
        if e.suggestion:
            print(f"   → {e.suggestion}", file=sys.stderr)
        return 1
    except KeyError as e:
        print(f"⛔ {e}", file=sys.stderr)
        return 1

    status = result.get("status", "unknown")
    message = result.get("message", "")
    print(f"[{cmd}] {status}: {message}")
    return 0 if status == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
