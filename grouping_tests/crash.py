import json
import logging
from typing import List, Optional

from sentry.eventstore.models import Event
from sentry.lang.native.applecrashreport import AppleCrashReport
from sentry.utils.safe import get_path
from sentry.grouping.component import GroupingComponent


LOG = logging.getLogger(__name__)


def get_crash_report(event: Event) -> Optional[str]:
    """ Return None if crash report fails. """
    try:
        return _get_crash_report(event)
    except Exception as e:
        LOG.warn("AppleCrashReport failed for event %s with exception %s", event.event_id, e)
        return None


def _get_crash_report(event: Event) -> str:
    # Copied from sentry/api/endpoints/event_apple_crash_report.py
    return str(
        AppleCrashReport(
            threads=get_path(event.data, "threads", "values", filter=True),
            context=event.data.get("contexts"),
            debug_images=get_path(event.data, "debug_meta", "images", filter=True),
            exceptions=get_path(event.data, "exception", "values", filter=True),
            symbolicated=True,
        )
    )


def dump_variants(config, event: Event) -> str:
    # Copied from sentry/tests/sentry/grouping/test_variants.py
    rv: List[str] = []
    for (key, value) in sorted(
        event.get_grouping_variants(force_config=config).items()
    ):
        if rv:
            rv.append("-" * 74)
        rv.append("%s:" % key)
        _dump_variant(value, rv, 1)

    return "\n".join(rv)


def _dump_variant(variant, lines=None, indent=0):
    # Copied from sentry/tests/sentry/grouping/test_variants.py
    if lines is None:
        lines = []

    def _dump_component(component, indent):
        if not component.hint and not component.values:
            return
        lines.append(
            "%s%s%s%s"
            % (
                "  " * indent,
                component.id,
                component.contributes and "*" or "",
                component.hint and " (%s)" % component.hint or "",
            )
        )
        for value in component.values:
            if isinstance(value, GroupingComponent):
                _dump_component(value, indent + 1)
            else:
                lines.append("{}{}".format("  " * (indent + 1), json.dumps(value)))

    lines.append("{}hash: {}".format("  " * indent, json.dumps(variant.get_hash())))
    for (key, value) in sorted(variant.__dict__.items()):
        if isinstance(value, GroupingComponent):
            lines.append("{}{}:".format("  " * indent, key))
            _dump_component(value, indent + 1)
        elif key == "config":
            # We do not want to dump the config
            continue
        else:
            lines.append("{}{}: {}".format("  " * indent, key, json.dumps(value)))

    return lines
