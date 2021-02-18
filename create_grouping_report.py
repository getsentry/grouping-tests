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
from report import HTMLReport, ProjectReport


LOG = logging.getLogger(__name__)

GROUP_TYPES = {
    'flat': ListNode,
    'tree': TreeNode,
}


@click.command()
@click.option("--event-dir", required=True, type=Path, help="created using store_events.py")
@click.option("--config", required=True, type=Path, help="Grouping config")
@click.option("--grouping-mode", required=True, type=click.Choice(GROUP_TYPES.keys()))
@click.option("--report-dir", required=True, type=Path, help="output directory")
@click.option("--events-base-url", type=str, help="Base URL for JSON links. Defaults to --event-dir")
def create_grouping_report(event_dir: Path, config: Path, report_dir: Path,
                           grouping_mode: str, events_base_url: str):
    """ Create a grouping report """

    if events_base_url is None:
        events_base_url = f"file://{event_dir.absolute()}"

    if report_dir.exists():
        LOG.error(f"Report dir {report_dir} already exists")
        sys.exit(1)

    os.makedirs(report_dir, exist_ok=True)

    with open(config, 'r') as config_file:
        config = json.load(config_file)

    report_metadata = write_metadata(report_dir, config)

    group_type = GROUP_TYPES[grouping_mode]

    project_ids = []
    for entry in os.scandir(event_dir):
        project_id = entry.name
        project_ids.append(project_id)

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
                item = extract_event_data(event)
                item['json_url'] = Path(filename).relative_to(event_dir)
                project.insert(flat_hashes, hierarchical_hashes, item)

        LOG.info("Project %s: Saving HTML report...", project_id)

        ProjectReport(project, report_dir, events_base_url)

    HTMLReport(report_dir, report_metadata, project_ids)


def extract_event_data(event: Event) -> dict:
    title, *subtitle = event.title.split(": ")

    return {
        'title': title,
        'subtitle': ": ".join(subtitle),
        'location': event.location
    }


def write_metadata(report_dir: Path, config: dict):

    meta = {
        'cli_args': sys.argv,
        'config': config,
        'grouping_tests_revision': git_revision()
    }

    with open(report_dir / "meta.json", 'w') as f:
        json.dump(meta, f, indent=4)

    return meta


def git_revision():
    git = Path(__file__).parent / ".git"
    with open(git /  "HEAD") as f:
        head = f.readline().strip().split(": ")[1]
    with open(git / head) as f:

        return f.readline().strip()


if __name__ == "__main__":
    create_grouping_report()  # pylint: disable=no-value-for-parameter
