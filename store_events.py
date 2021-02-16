# prelude of careful imports so django app is correctly initialized
from sentry.runner import configure
import os
os.environ["SENTRY_CONF"] = "../getsentry/getsentry/settings.py"
configure()

import logging
import click
from concurrent.futures import ProcessPoolExecutor
import sys
import json
import textwrap
import time
from pathlib import Path

from sentry import nodestore
from sentry.eventstore.models import Event

import sentry_sdk
sentry_sdk.init("")


@click.command()
@click.option("--output-dir", required=True, type=Path)
@click.option("--num-workers", default=1)
def store_events(output_dir: Path, num_workers: int):
    """ Store event payloads as JSON files

    Usage example:

        clickhouse-client --query 'SELECT project_id, event_id FROM sentry_local LIMIT 100' | python store_events.py --output-dir ./events

    """

    if output_dir.exists():
        print(f"ERROR: Output dir {output_dir} already exists")
        sys.exit(1)

    t0 = time.time()

    print("Reading event IDs from stdin...")
    lines = list(sys.stdin)  # So we have a length for the progress bar

    with ProcessPoolExecutor(max_workers=num_workers) as pool:
        tasks = pool.map(fetch, lines)
        progress_bar = click.progressbar(tasks, length=len(lines))

        with progress_bar as nodes:
            for project_id, event_id, node in nodes:
                if node is None:
                    print(
                        "WARNING: Got None from nodestore for project / event",
                        project_id, event_id, file=sys.stderr)
                else:
                    store(project_id, event_id, node, output_dir)

    print("Done. Time ellapsed: %s" % (time.time() - t0))


def fetch(line):
    project_id, event_id = line.strip().split("\t")
    node_id = Event.generate_node_id(project_id, event_id)

    return project_id, event_id, nodestore.get(node_id)  # pylint: disable=no-member


def store(project_id, event_id, node, output_dir: Path):
    output_path = output_dir / f"project_{project_id}" / event_path(event_id)
    os.makedirs(output_path.parent, exist_ok=True)
    with open(output_path, 'w') as output_file:
        json.dump(node, output_file)


def event_path(event_id: str, prefix_length=2, num_levels=2) -> Path:
    """ Spread out files by chopping up the event ID """
    id_parts = textwrap.wrap(event_id, prefix_length)
    target_dir = Path().joinpath(*id_parts[:num_levels])

    return target_dir / f"event_{event_id}.json"


if __name__ == "__main__":
    store_events()  # pylint: disable=no-value-for-parameter
