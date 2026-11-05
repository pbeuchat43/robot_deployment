#!/usr/bin/env python3
"""Compatibility path for the installed prepared launch interface."""
# Copyright (c) 2026 Paul N. Beuchat. MIT License.
from robot_deployment.launch import main

if __name__ == "__main__":
    raise SystemExit(main())
