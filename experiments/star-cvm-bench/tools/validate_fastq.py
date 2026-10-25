#!/usr/bin/env python3
"""Validate the four-line paired FASTQ format used by these ENA input sets."""
import argparse
import json
import sys


def validate(left, right, expected):
    count = 0
    with open(left) as a, open(right) as b:
        while True:
            ra, rb = [a.readline() for _ in range(4)], [b.readline() for _ in range(4)]
            if not ra[0] and not rb[0]:
                break
            for r in (ra, rb):
                if not all(r) or not r[0].startswith('@') or not r[2].startswith('+'):
                    raise ValueError('Incomplete or malformed FASTQ record')
                if not r[1].strip() or len(r[1].strip()) != len(r[3].strip()):
                    raise ValueError('Sequence/quality length mismatch')
            names = [r[0].split()[0].removesuffix('/1').removesuffix('/2') for r in (ra, rb)]
            if names[0] != names[1]:
                raise ValueError('Paired names differ')
            count += 1
    if count != expected:
        raise ValueError(f'Expected {expected} pairs, found {count}')
    return count


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('left'); p.add_argument('right'); p.add_argument('--pairs', type=int, required=True)
    args = p.parse_args()
    try:
        if args.pairs <= 0:
            raise ValueError('Pair count must be positive')
        print(json.dumps({'validated_pairs': validate(args.left, args.right, args.pairs)}))
    except (OSError, ValueError) as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
