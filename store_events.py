# prelude of careful imports so django app is correctly initialized
from sentry.runner import configure
import os
os.environ["SENTRY_CONF"] = "../getsentry/getsentry/settings.py"
configure()

import logging
import click
import sys
import json
import textwrap
from pathlib import Path

from sentry import nodestore
from sentry.eventstore.models import Event

import sentry_sdk
sentry_sdk.init("")


@click.command()
@click.option("--output-dir", required=True, type=Path)
def store_events(output_dir: Path):
    """ Store event payloads as JSON files

    Usage example:

        clickhouse-client --query 'SELECT project_id, event_id FROM sentry_local LIMIT 100' | python store_events.py --output-dir ./events

    """

    if output_dir.exists():
        print(f"Output dir {output_dir} already exists", file=sys.stderr)
        sys.exit(1)

    print("Reading event IDs from stdin...")

    for line in sys.stdin:
        project_id, event_id = line.strip().split("\t")
        node_id = Event.generate_node_id(project_id, event_id)
        node = nodestore.get(node_id)

        if node is not None:
            output_path = output_dir / f"project_{project_id}" / event_path(event_id)
            os.makedirs(output_path.parent, exist_ok=True)
            with open(output_path, 'w') as output_file:
                json.dump(node, output_file)

    print("Done.")


def event_path(event_id: str, prefix_length=2, num_levels=2) -> Path:
    """ Spread out files by chopping up the event ID """
    id_parts = textwrap.wrap(event_id, prefix_length)
    target_dir = Path().joinpath(*id_parts[:num_levels])

    return target_dir / f"event_{event_id}.json"


if __name__ == "__main__":
    store_events()  # pylint: disable=no-value-for-parameter
