# prelude of careful imports so django app is correctly initialized
from sentry.runner import configure
import os
os.environ["SENTRY_CONF"] = "../getsentry/getsentry/settings.py"
configure()


import logging
import click
import sys
import json
from glob import iglob
from pathlib import Path
from typing import List, Dict
import os

from sentry.event_manager import materialize_metadata
from sentry.eventstore.models import Event

import sentry_sdk
sentry_sdk.init("")

from config import Config
from grouping import generate_hashes
from tree import GroupNode


LOG = logging.getLogger(__name__)


@click.command()
@click.option("--event-dir", required=True, type=Path, help="created using store_events.py")
@click.option("--config", required=True, type=Config, help="Grouping config")
@click.option("--report-dir", required=True, type=Path, help="output directory")
def create_grouping_report(event_dir: Path, config: Config, report_dir: Path):
    """ Create a grouping report """

    if report_dir.exists():
        LOG.error(f"Report dir {report_dir} already exists")
        sys.exit(1)

    # TODO: instead of using the stored production hashes, use Event.get_hashes(force_config=...)
    #       to create a new group tree
    for entry in os.scandir(event_dir):
        project_id = entry.name

        # Create an issue tree
        project = GroupNode(project_id)

        for filename in iglob(f"{entry.path}/**/*json", recursive=True):
            with open(filename, 'r') as file_:
                event_data = json.load(file_)
            event_id = event_data['event_id']
            event = Event(project_id, event_id, group_id=None, data=event_data)
            try:
                node_path = generate_hashes(event, config)
            except KeyError:
                LOG.warn("Event %s has no hashes", event_id)
            else:
                # Store lightweight version of event, keep payload in filesystem
                metadata = materialize_metadata(event.data)
                project.insert(node_path, metadata)

        project.visit(print_node)


def print_node(node: GroupNode, depth: int):
    if node.items:
        node_title = node.items[-1]['title']
    else:
        node_title = node.name
    print_indented(2*depth, f"{node_title} ({node.item_count} events)")


def print_indented(num_spaces: int, *args, **kwargs):
    for _ in range(num_spaces):
        sys.stdout.write(" ")
    print(*args, **kwargs)


if __name__ == "__main__":
    create_grouping_report()  # pylint: disable=no-value-for-parameter
