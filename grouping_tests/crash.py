from sentry.eventstore.models import Event
from sentry.api.bases.project import ProjectEndpoint
from sentry.api.exceptions import ResourceDoesNotExist
from sentry.lang.native.applecrashreport import AppleCrashReport
from sentry.utils.safe import get_path


def get_crash_report(event: Event) -> str:
    # Copied from sentry/api/endpoints/event_apple_crash_report.py
    return str(
        AppleCrashReport(
            threads=get_path(event.data, "threads", "values", filter=True),
            context=event.data.get("contexts"),
            debug_images=get_path(event.data, "debug_meta", "images", filter=True),
            exceptions=get_path(event.data, "exception", "values", filter=True),
            symbolicated=False,  # TODO
        )
    )