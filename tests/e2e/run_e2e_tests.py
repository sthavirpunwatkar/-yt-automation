#!/usr/bin/env python3
"""E2E Test Runner for yt-automation."""
from __future__ import annotations

import argparse
import sys
import subprocess
from pathlib import Path

def main() -> None:
    parser = argparse.ArgumentParser(description="Run E2E tests for yt-automation.")
    parser.add_argument(
        "--tier",
        default="all",
        choices=["1", "2", "3", "4", "all"],
        help="Test tier to run (1, 2, 3, 4, or all)"
    )
    parser.add_argument(
        "--mode",
        default="mocked",
        choices=["mocked", "live"],
        help="Testing mode (mocked or live)"
    )
    # Allow passing extra pytest arguments
    args, extra_args = parser.parse_known_args()

    cmd = [sys.executable, "-m", "pytest"]
    
    # Map tier to pytest markers
    if args.tier != "all":
        cmd += ["-m", f"tier{args.tier}"]
        
    cmd += [f"--mode={args.mode}"]
    cmd += [f"--tier={args.tier}"]
    cmd += extra_args

    print(f"Running E2E tests command: {' '.join(cmd)}")
    
    # Run the pytest command
    res = subprocess.run(cmd)
    sys.exit(res.returncode)

if __name__ == "__main__":
    main()
