# pylint: disable=wrong-import-position
# pylint: disable=wrong-import-order
# pylint: disable=ungrouped-imports
# prelude of careful imports so django app is correctly initialized
from sentry.runner import configure
configure()

import click
from multiprocessing import Manager
import sys
import json
import textwrap
import time
from pathlib import Path
import os

from sentry import nodestore
from sentry.eventstore.models import Event

import sentry_sdk
sentry_sdk.init("")


global_output_dir = None  # Used in fetch_and_store


@click.command()
@click.option("--output-dir", required=True, type=Path)
@click.option("--num-workers", type=int, help="Defaults to Python multiprocessing default")
def store_events(output_dir: Path, num_workers: int):
    """ Store event payloads as JSON files

    Usage example:

        clickhouse-client --query 'SELECT project_id, event_id FROM sentry_local LIMIT 100' \\
            | python store_events.py --output-dir ./events

    """
    global global_output_dir  # pylint: disable=global-statement
    global_output_dir = output_dir

    if output_dir.exists():
        print(f"ERROR: Output dir {output_dir} already exists")
        sys.exit(1)

    t0 = time.time()

    print("Reading event IDs from stdin...")
    lines = list(sys.stdin)  # So we have a length for the progress bar

    print("Fetching event payloads...")
    with Manager() as manager:
        with manager.Pool(num_workers) as pool:  # type: ignore
            tasks = pool.imap_unordered(fetch_and_store, lines)
            progress_bar = click.progressbar(tasks, length=len(lines))

            with progress_bar as results:
                for _ in results:
                    pass


    print("Done. Time ellapsed: %s" % (time.time() - t0))


def fetch_and_store(line):
    project_id, event_id = line.strip().split("\t")
    event_id = event_id.replace("-", "")
    node_id = Event.generate_node_id(project_id, event_id)
    node = nodestore.get(node_id)  # pylint: disable=no-member

    if node is None:
        print(
            "WARNING: Got None from nodestore for project / event",
            project_id, event_id, file=sys.stderr)
    else:
        store(project_id, event_id, node, global_output_dir)


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
