"""Health check for the Wiseweb-AI backend.

Usage (from backend/):
  python -m scripts.health_check [--url http://localhost:8000]
"""

import argparse
import sys

import httpx


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000/api/v1/health")
    args = parser.parse_args()
    try:
        response = httpx.get(args.url, timeout=5)
        response.raise_for_status()
        print(f"OK: {response.json()}")
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
