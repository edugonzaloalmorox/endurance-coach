"""Command-line entry point for safe, implemented project operations."""

import argparse
import json
from pathlib import Path

from endurance_coach.config import OllamaSettings, StorageSettings
from endurance_coach.metrics import summarize_training
from endurance_coach.sample_data import synthetic_activities, write_synthetic_activities
from endurance_coach.storage import StorageError, database_status, initialize_database


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser for implemented local operations.

    Returns:
        Configured argument parser.
    """
    parser = argparse.ArgumentParser(prog="endurance-coach")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("config", help="show the resolved local-model configuration")
    database = subparsers.add_parser("db", help="manage the local training database")
    database_commands = database.add_subparsers(dest="database_command", required=True)
    database_commands.add_parser("init", help="initialize or upgrade the local database")
    database_commands.add_parser("status", help="show safe schema and row-count status")
    metrics = subparsers.add_parser("metrics", help="summarize the bundled synthetic rides")
    metrics.add_argument("--ftp", type=int, default=250)
    generate = subparsers.add_parser("generate-data", help="write deterministic sample rides")
    generate.add_argument(
        "destination", type=Path, nargs="?", default=Path("data/synthetic_activities.json")
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Execute one CLI command.

    Args:
        argv: Optional arguments excluding the executable name.

    Returns:
        Zero on success or two for a safely reported storage failure.
    """
    args = build_parser().parse_args(argv)
    if args.command == "config":
        print(OllamaSettings.from_env().model_dump_json(indent=2))
    elif args.command == "db":
        settings = StorageSettings.from_env()
        try:
            status = (
                initialize_database(settings.database_path)
                if args.database_command == "init"
                else database_status(settings.database_path)
            )
        except StorageError as exc:
            print(json.dumps({"error": str(exc)}))
            return 2
        print(json.dumps(status.as_dict(), indent=2, sort_keys=True))
    elif args.command == "metrics":
        print(summarize_training(synthetic_activities(), args.ftp).model_dump_json(indent=2))
    elif args.command == "generate-data":
        write_synthetic_activities(args.destination)
        print(f"Wrote synthetic activities to {args.destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
