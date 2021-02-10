import logging
import click
import sys
import json
from glob import iglob
from pathlib import Path
from typing import List, Dict
import os


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

    # Create an issue tree
    root_node = GroupNode("root")

    # TODO: instead of using the stored production hashes, use Event.get_hashes(force_config=...)
    #       to create a new group tree
    for entry in os.scandir(event_dir):
        project_id = entry.name
        for filename in iglob(f"{entry.path}/**/*json", recursive=True):
            with open(filename, 'r') as file_:
                event = json.load(file_)
            try:
                node_path = [project_id] + event['hashes']
            except KeyError:
                LOG.warn("Event %s has no hashes", event['event_id'])
            else:
                # Store lightweight version of event, keep payload in filesystem
                root_node.insert(node_path, filename)

    root_node.visit(print_graph)


class GroupNode:

    def __init__(self, name: str):

        self.name = name
        self.item_count = 0
        self._items = []
        self._children: Dict[str, GroupNode] = {}

    def insert(self, path: List[str], item):
        if path:
            head, *tail = path
            self._child(head).insert(tail, item)
        else:
            self._items.append(item)
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


def print_graph(node: GroupNode, depth: int):
    print_indented(2*depth, f"{node.name} ({node.item_count})")


def print_indented(num_spaces: int, *args, **kwargs):
    for _ in range(num_spaces):
        sys.stdout.write(" ")
    print(*args, **kwargs)


if __name__ == "__main__":
    create_grouping_report()
