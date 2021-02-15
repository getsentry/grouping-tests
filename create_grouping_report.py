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

import sentry_sdk
sentry_sdk.init("")

LOG = logging.getLogger(__name__)


@click.command()
@click.option("--event-dir", required=True, type=Path, help="created using store_events.py")
@click.option("--config", required=True, type=Path, help="Grouping config")
@click.option("--report-dir", required=True, type=Path, help="output directory")
def create_grouping_report(event_dir: Path, config: Path, report_dir: Path):
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
                event = json.load(file_)
            try:
                node_path = event['hashes']
            except KeyError:
                LOG.warn("Event %s has no hashes", event['event_id'])
            else:
                # Store lightweight version of event, keep payload in filesystem
                metadata = materialize_metadata(event)
                project.insert(node_path, metadata)

        project.visit(print_node)


class GroupNode:

    def __init__(self, name: str):

        self.name = name
        self.item_count = 0
        self.items = []
        self._children: Dict[str, GroupNode] = {}

    def insert(self, path: List[str], item):
        if path:
            head, *tail = path
            self._child(head).insert(tail, item)
        else:
            self.items.append(item)
        self.item_count += 1

    def visit(self, visitor, depth=0):
        visitor(self, depth)
        for child in self._children.values():
            child.visit(visitor, depth + 1)

    def _child(self, name):
        if name not in self._children:
            child = self._children[name] = GroupNode(name)
        else:
            child = self._children[name]

        return child


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
