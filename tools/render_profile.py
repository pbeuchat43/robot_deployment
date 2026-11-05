#!/usr/bin/env python3
"""Source-checkout adapter; install robot_deployment in the chosen environment."""
# Copyright (c) 2026 Paul N. Beuchat. MIT License.
import argparse
from pathlib import Path
from robot_deployment.profile import render

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--definitions", type=Path)
    args = parser.parse_args()
    print(render(args.site, args.release, args.output, root=args.definitions))
