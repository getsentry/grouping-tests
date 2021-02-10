# prelude of careful imports so django app is correctly initialized
from sentry.runner import configure
import os
os.environ["SENTRY_CONF"] = "../getsentry/getsentry/settings.py"
configure()

from sentry import nodestore
from sentry.eventstore.models import Event
import logging
import click
import sys
import json
from pathlib import Path


LOG = logging.getLogger(__name__)


@click.command()
@click.option("--output-dir", required=True, type=Path)
def store_events(output_dir: str):
    """ Store event payloads as JSON files

    Usage example:

        clickhouse-client --query 'SELECT project_id, event_id FROM sentry_local LIMIT 100' | python store_events.py --output-dir ./events

    """

    if output_dir.exists():
        LOG.error(f"Output dir {output_dir} already exists")
        sys.exit(1)

    LOG.info("Reading event IDs from stdin...")

    for line in sys.stdin:
        project_id, event_id = line.strip().split("\t")
        node_id = Event.generate_node_id(project_id, event_id)
        node = nodestore.get(node_id)

        output_path = output_dir / f"project_{project_id}" / f"event_{event_id}.json"
        os.makedirs(output_path.parent)
        with open(output_path, 'w') as output_file:
            json.dump(node, output_file)

    LOG.info("Done.")


if __name__ == "__main__":
    store_events()
