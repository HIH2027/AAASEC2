"""Command-line entry point for the Medication Safety Agent."""

import argparse

from .agent import run_agent


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the Medication Safety Agent on a de-identified profile"
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Use the deterministic summary without an LLM request",
    )
    args = parser.parse_args()
    print(run_agent(offline=args.offline))


if __name__ == "__main__":
    main()
