#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


REQUIRED_REPO_PATHS = [
    "yf_marketdata/__main__.py",
    "yf_marketdata/config.py",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the existing yf_marketdata exporter from a checked-out repo.")
    parser.add_argument("--repo-path", required=True, help="Path to a local dachent/yf_marketdata checkout.")
    parser.add_argument("--config-path", required=True, help="Path to the YAML config file to pass to yf_marketdata.")
    parser.add_argument("--python", default=sys.executable, help="Python interpreter to use.")
    return parser.parse_args()


def validate_repo(repo_path: Path) -> None:
    if not repo_path.exists() or not repo_path.is_dir():
        raise ValueError(f"Repo path does not exist or is not a directory: {repo_path}")
    missing = [relative for relative in REQUIRED_REPO_PATHS if not (repo_path / relative).exists()]
    if missing:
        raise ValueError(f"Repo path does not look like yf_marketdata. Missing: {', '.join(missing)}")


def validate_config(config_path: Path) -> None:
    if not config_path.exists() or not config_path.is_file():
        raise ValueError(f"Config path does not exist or is not a file: {config_path}")


def main() -> int:
    args = parse_args()
    repo_path = Path(args.repo_path).expanduser().resolve()
    config_path = Path(args.config_path).expanduser().resolve()

    try:
        validate_repo(repo_path)
        validate_config(config_path)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    command = [args.python, "-m", "yf_marketdata", str(config_path)]
    print(f"Running in {repo_path}: {' '.join(command)}")
    completed = subprocess.run(command, cwd=repo_path)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
