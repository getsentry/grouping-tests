from collections import UserDict
from pathlib import Path
import os

from sentry.eventstore.models import Event

from grouping_tests.utils import event_path


class EventItem(UserDict):

    def __init__(self, event: Event, root_dir: Path):
        super(EventItem, self).__init__(_extract_event_data(event))
        self.on_disk = DiskStore(root_dir / event_path(event.event_id))


class DiskStore:

    def __init__(self, path: Path):
        self._path = path
        os.makedirs(path, exist_ok=True)

    def __setitem__(self, key: str, value: str):
        with open(self._path / key, 'w') as f:
            f.write(value)


def _extract_event_data(event: Event) -> dict:
    title, *tail = event.title.split(": ", 1)

    subtitle = tail[0] if tail else event.data.get('metadata', {}).get('value')

    return {
        'event_id': event.event_id,
        'title': title,
        'subtitle': subtitle,
        'culprit': event.culprit
    }