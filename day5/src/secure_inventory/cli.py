"""Command-line entry point for the Secure Inventory Agent."""

import argparse

from .agent import run_agent


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Secure Inventory Agent")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Use deterministic recommendations without an LLM request",
    )
    args = parser.parse_args()
    print(run_agent(offline=args.offline))


if __name__ == "__main__":
    main()
