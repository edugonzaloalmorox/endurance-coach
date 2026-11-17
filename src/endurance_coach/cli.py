"""Command-line entry point for safe, implemented project operations."""

import argparse
import json
from datetime import date
from pathlib import Path

from endurance_coach.config import IntervalsSettings, OllamaSettings, StorageSettings
from endurance_coach.ingestion import FitIngestionError
from endurance_coach.integrations import IntervalsClient, IntervalsError
from endurance_coach.metrics import summarize_training
from endurance_coach.sample_data import synthetic_activities, write_synthetic_activities
from endurance_coach.services import (
    IntervalsSyncError,
    import_fit_archive,
    sync_intervals_activities,
)
from endurance_coach.storage import StorageError, database_status, initialize_database


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def _iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an ISO date (YYYY-MM-DD)") from exc


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
    import_fit = database_commands.add_parser(
        "import-fit", help="import FIT and FIT.GZ activities from a local archive"
    )
    import_fit.add_argument(
        "archive",
        type=Path,
        nargs="?",
        help="archive root (defaults to ENDURANCE_COACH_ARCHIVE_PATH)",
    )
    import_fit.add_argument(
        "--dry-run",
        action="store_true",
        help="discover and parse inputs without changing the database",
    )
    import_fit.add_argument(
        "--metadata-csv",
        type=Path,
        help="Strava-style activities.csv inside the archive (auto-detected at archive root)",
    )
    import_fit.add_argument(
        "--max-file-mib",
        type=_positive_int,
        default=128,
        help="maximum compressed or plain artifact size (default: 128)",
    )
    import_fit.add_argument(
        "--max-content-mib",
        type=_positive_int,
        default=1024,
        help="maximum decompressed FIT payload size (default: 1024)",
    )
    sync_intervals = database_commands.add_parser(
        "sync-intervals",
        help="incrementally retrieve and store read-only Intervals.icu summaries",
    )
    sync_intervals.add_argument(
        "--oldest",
        type=_iso_date,
        help="initial or explicit inclusive start date (YYYY-MM-DD)",
    )
    sync_intervals.add_argument(
        "--newest",
        type=_iso_date,
        help="inclusive end date (defaults to today)",
    )
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
            if args.database_command == "import-fit":
                archive = args.archive or settings.archive_path
                if archive is None:
                    raise FitIngestionError("archive_not_configured")
                summary = import_fit_archive(
                    archive,
                    settings.database_path,
                    dry_run=args.dry_run,
                    metadata_csv=args.metadata_csv,
                    max_raw_bytes=args.max_file_mib * 1024 * 1024,
                    max_content_bytes=args.max_content_mib * 1024 * 1024,
                )
                print(json.dumps(summary.as_dict(), indent=2, sort_keys=True))
                return 0 if summary.failed == 0 and summary.metadata_failed == 0 else 1
            if args.database_command == "sync-intervals":
                intervals_settings = IntervalsSettings.from_env()
                summary = sync_intervals_activities(
                    settings.database_path,
                    IntervalsClient(intervals_settings),
                    oldest=args.oldest,
                    newest=args.newest,
                )
                print(json.dumps(summary.as_dict(), indent=2, sort_keys=True))
                return 0
            status = (
                initialize_database(settings.database_path)
                if args.database_command == "init"
                else database_status(settings.database_path)
            )
        except (
            FitIngestionError,
            IntervalsError,
            IntervalsSyncError,
            StorageError,
            ValueError,
        ) as exc:
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
