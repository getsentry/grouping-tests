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
import textwrap
import time
from pathlib import Path


LOG = logging.getLogger(__name__)

BATCH_SIZE = 100  # determined empirically


@click.command()
@click.option("--output-dir", required=True, type=Path)
def store_events(output_dir: Path):
    """ Store event payloads as JSON files

    Usage example:

        clickhouse-client --query 'SELECT project_id, event_id FROM sentry_local LIMIT 100' | python store_events.py --output-dir ./events

    """

    if output_dir.exists():
        LOG.error(f"Output dir {output_dir} already exists")
        sys.exit(1)

    LOG.info("Reading event IDs from stdin...")

    t0 = time.time()

    for batch in read_batches():

        id_pairs = (line.strip().split("\t") for line in batch)
        id_map = {
            Event.generate_node_id(project_id, event_id): (project_id, event_id)
            for project_id, event_id in id_pairs
        }
        nodes_by_id = nodestore.get_multi(id_map.keys())

        for node_id, node in nodes_by_id.items():
            project_id, event_id = id_map[node_id]
            if node is not None:
                output_path = output_dir / f"project_{project_id}" / event_path(event_id)
                write_node(node, output_path)

    LOG.info("Done. Seconds ellapsed: %s" % (time.time() - t0))


def write_node(node, output_path):
    os.makedirs(output_path.parent, exist_ok=True)
    with open(output_path, 'w') as output_file:
        json.dump(node, output_file)


def read_batches():
    batch = []
    for i, line in enumerate(sys.stdin):
        batch.append(line)
        if i > 0 and (i % BATCH_SIZE) == 0:
            yield batch
            batch = []

    if batch:
        yield batch



def event_path(event_id: str) -> Path:
    """ Return relative event path """
    id_parts = textwrap.wrap(event_id, 8)
    target_dir = Path().joinpath(*id_parts)

    return target_dir / f"event_{event_id}.json"


if __name__ == "__main__":
    store_events()
