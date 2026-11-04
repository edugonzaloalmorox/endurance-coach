"""Command-line entry point for safe, implemented project operations."""

import argparse
from pathlib import Path

from endurance_coach.config import OllamaSettings
from endurance_coach.metrics import summarize_training
from endurance_coach.sample_data import synthetic_activities, write_synthetic_activities


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="endurance-coach")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("config", help="show the resolved local-model configuration")
    metrics = subparsers.add_parser("metrics", help="summarize the bundled synthetic rides")
    metrics.add_argument("--ftp", type=int, default=250)
    generate = subparsers.add_parser("generate-data", help="write deterministic sample rides")
    generate.add_argument(
        "destination", type=Path, nargs="?", default=Path("data/synthetic_activities.json")
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "config":
        print(OllamaSettings.from_env().model_dump_json(indent=2))
    elif args.command == "metrics":
        print(summarize_training(synthetic_activities(), args.ftp).model_dump_json(indent=2))
    elif args.command == "generate-data":
        write_synthetic_activities(args.destination)
        print(f"Wrote synthetic activities to {args.destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
