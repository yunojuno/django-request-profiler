from datetime import date, timedelta
from typing import Any

from django.core.management.base import BaseCommand, CommandParser
from django.utils.timezone import now as tz_now
from django.utils.translation import gettext_lazy as _lazy

from request_profiler.models import ProfilingRecord
from request_profiler.settings import LOG_TRUNCATION_DAYS


class Command(BaseCommand):

    help = "Truncate the profiler log after a specified number days."

    def add_arguments(self, parser: CommandParser) -> None:
        super().add_arguments(parser)
        parser.add_argument(
            "-d",
            "--days",
            dest="days",
            type=int,
            default=LOG_TRUNCATION_DAYS,
            help=_lazy(
                "Number of days after which to truncate logs. "
                "Defaults to REQUEST_PROFILER_LOG_TRUNCATION_DAYS."
            ),
        )
        parser.add_argument(
            "--commit",
            action="store_true",
            help=_lazy(
                "Use --commit to commit the deletion. Without this the "
                " command is a 'dry-run'."
            ),
        )

    def handle(self, *args: Any, **options: Any) -> None:
        self.stdout.write(
            f"request_profiler: truncating request_profile logs at {tz_now()}"
        )
        if (days := options["days"]) == 0:
            self.stdout.write(
                "request_profiler: aborting truncation as truncation limit is set to 0"
            )
            return
        cutoff = date.today() - timedelta(days=days)
        self.stdout.write(f"request_profiler: truncation cutoff: {cutoff}")
        logs = ProfilingRecord.objects.filter(start_ts__date__lt=cutoff)
        self.stdout.write(f"request_profiler: found {logs.count()} records to delete.")
        if not options["commit"]:
            self.stderr.write(
                "request_profiler: aborting truncation as --commit option is not set."
            )
            return
        count, _ = logs.delete()
        self.stdout.write(f"request_profiler: deleted {count} log records.")
        self.stdout.write(f"request_profiler: truncation completed at {tz_now()}")
