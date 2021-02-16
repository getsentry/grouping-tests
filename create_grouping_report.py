# prelude of careful imports so django app is correctly initialized
from sentry.runner import configure
import os
os.environ["SENTRY_CONF"] = "../getsentry/getsentry/settings.py"
configure()


import logging
import click
import sys
import json
import glob
from pathlib import Path
from typing import List, Dict
import os

from sentry.event_manager import materialize_metadata
from sentry.eventstore.models import Event

import sentry_sdk
sentry_sdk.init("")

from groups.base import GroupNode
from groups.flat import ListNode
from groups.tree import TreeNode
from report import HTMLReport


LOG = logging.getLogger(__name__)

GROUP_TYPES = {
    'flat': ListNode,
    'tree': TreeNode,
}


@click.command()
@click.option("--event-dir", required=True, type=Path, help="created using store_events.py")
@click.option("--config", required=True, type=Path, help="Grouping config")
@click.option("--report-dir", required=True, type=Path, help="output directory")
@click.option("--grouping-mode", required=True, type=click.Choice(GROUP_TYPES.keys()))
def create_grouping_report(event_dir: Path, config: Path, report_dir: Path, grouping_mode):
    """ Create a grouping report """

    if report_dir.exists():
        LOG.error(f"Report dir {report_dir} already exists")
        sys.exit(1)

    os.makedirs(report_dir, exist_ok=True)

    with open(config, 'r') as config_file:
        config = json.load(config_file)

    write_metadata(report_dir, config)

    group_type = GROUP_TYPES[grouping_mode]

    for entry in os.scandir(event_dir):
        project_id = entry.name

        # Create a root node for all groups
        project = group_type(project_id)

        LOG.info("Project %s: Collecting filenames...", project_id)
        # iglob would be easier on memory, but we want to use the progress bar
        filenames = glob.glob(f"{entry.path}/**/*json", recursive=True)

        LOG.info("Project %s: Processing...", project_id)
        with click.progressbar(filenames) as progress_bar:
            for filename in progress_bar:
                with open(filename, 'r') as file_:
                    event_data = json.load(file_)
                event_id = event_data['event_id']
                event = Event(project_id, event_id, group_id=None, data=event_data)

                flat_hashes, hierarchical_hashes = event.get_hashes(force_config=config)

                # Store lightweight version of event, keep payload in filesystem
                metadata = materialize_metadata(event.data)
                project.insert(flat_hashes, hierarchical_hashes, metadata)

        HTMLReport(project, report_dir)


def write_metadata(report_dir: Path, config: dict):

    meta = {
        'cli_args': sys.argv,
        'config': config,
        'grouping_tests_revision': git_revision()
    }

    with open(report_dir / "meta.json", 'w') as f:
        json.dump(meta, f, indent=4)


def git_revision():
    git = Path(__file__).parent / ".git"
    with open(git /  "HEAD") as f:
        head = f.readline().strip().split(": ")[1]
    with open(git / head) as f:

        return f.readline().strip()


if __name__ == "__main__":
    create_grouping_report()  # pylint: disable=no-value-for-parameter
