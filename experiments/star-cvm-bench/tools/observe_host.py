#!/usr/bin/env python3
"""Bounded, unprivileged host pressure observations; no process identities."""
import argparse
import json
import math
from pathlib import Path
import signal
import time

from star_bench import host_observation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, required=True)
    parser.add_argument("--interval", type=float, default=1)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    if not (math.isfinite(args.seconds) and 0 < args.seconds <= 86400
            and math.isfinite(args.interval) and 0.1 <= args.interval <= args.seconds):
        parser.error("Use 0 < seconds <= 86400 and 0.1 <= interval <= seconds")
    stop = False
    def finish(signum, frame):
        nonlocal stop
        stop = True
    signal.signal(signal.SIGTERM, finish)
    signal.signal(signal.SIGINT, finish)
    deadline = time.monotonic() + args.seconds
    with Path(args.out).open("x") as f:
        while not stop and time.monotonic() < deadline:
            f.write(json.dumps(host_observation(), sort_keys=True) + "\n")
            f.flush()
            time.sleep(min(args.interval, max(0, deadline - time.monotonic())))


if __name__ == "__main__":
    main()
