from typing import List

from sentry.grouping import api as grouping_api
from sentry.eventstore.models import Event
from sentry.stacktraces.processing import normalize_stacktraces_for_grouping

from config import Config


def generate_hashes(event: Event, config: Config) -> List[str]:
    """ Generate grouping hashes for a single event """
    if config.normalize_stacktraces:
        normalize_stacktraces_for_grouping(event.data, config.grouping_config)

    return grouping_api.get_grouping_variants_for_event(event, config.grouping_config)
