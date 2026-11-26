"""Command-line entry point for safe, implemented project operations."""

import argparse
import json
from datetime import date
from pathlib import Path

from endurance_coach.analysis import MissingTrainingDataError, summarize_training
from endurance_coach.config import (
    CorosSettings,
    IntervalsSettings,
    OllamaSettings,
    StorageSettings,
)
from endurance_coach.fixtures import synthetic_activities, write_synthetic_activities
from endurance_coach.ingestion import FitIngestionError
from endurance_coach.integrations import CorosClient, CorosError, IntervalsClient, IntervalsError
from endurance_coach.llm import AgentRuntime, AgentRuntimeError
from endurance_coach.services import (
    IntervalsSyncError,
    import_fit_archive,
    sync_intervals_activities,
)
from endurance_coach.skills import SkillLoader
from endurance_coach.storage import (
    StorageError,
    database_status,
    initialize_database,
    inspect_database,
    load_recent_training_activities,
)


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
    ask = subparsers.add_parser(
        "ask", help="answer a coaching question from recent local training data"
    )
    ask.add_argument("question", help="coaching question for the local model")
    ask.add_argument(
        "--limit",
        type=_positive_int,
        default=50,
        help="maximum recent cycling activities to analyze, up to 500 (default: 50)",
    )
    coros = subparsers.add_parser(
        "coros", help="access supplementary recovery data through read-only COROS MCP tools"
    )
    coros_commands = coros.add_subparsers(dest="coros_command", required=True)
    coros_commands.add_parser(
        "discover", help="authorize if needed and show allowed available tools"
    )
    recovery = coros_commands.add_parser(
        "recovery", help="retrieve a bounded supplementary recovery snapshot"
    )
    recovery.add_argument(
        "--days",
        type=_positive_int,
        default=7,
        help="number of recent days, from 1 through 30 (default: 7)",
    )
    database = subparsers.add_parser("db", help="manage the local training database")
    database_commands = database.add_subparsers(dest="database_command", required=True)
    database_commands.add_parser("init", help="initialize or upgrade the local database")
    database_commands.add_parser("status", help="show safe schema and row-count status")
    inspect = database_commands.add_parser(
        "inspect", help="show recent normalized activities without GPS tracks"
    )
    inspect.add_argument(
        "--limit",
        type=_positive_int,
        default=20,
        help="maximum recent activities to show, up to 100 (default: 20)",
    )
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
    elif args.command == "coros":
        try:
            client = CorosClient(CorosSettings.from_env())
            result = (
                client.discover_tools()
                if args.coros_command == "discover"
                else client.recovery_snapshot(args.days)
            )
        except (CorosError, ValueError) as exc:
            print(json.dumps({"error": str(exc)}))
            return 2
        print(result.model_dump_json(indent=2))
    elif args.command == "ask":
        storage_settings = StorageSettings.from_env()
        ollama_settings = OllamaSettings.from_env()
        try:
            if args.limit > 500:
                raise ValueError("training activity limit must be between 1 and 500")
            activities = load_recent_training_activities(
                storage_settings.database_path,
                limit=min(args.limit, ollama_settings.max_context_activities),
            )
            recommendation = AgentRuntime(
                settings=ollama_settings,
                skill_loader=SkillLoader(Path("coach_skills")),
            ).run(args.question, activities, current_date=date.today())
        except (
            AgentRuntimeError,
            MissingTrainingDataError,
            StorageError,
            ValueError,
        ) as exc:
            print(json.dumps({"error": str(exc)}))
            return 2
        print(recommendation.model_dump_json(indent=2))
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
            if args.database_command == "inspect":
                inspection = inspect_database(settings.database_path, limit=args.limit)
                print(json.dumps(inspection.as_dict(), indent=2, sort_keys=True))
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
