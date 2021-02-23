# prelude of careful imports so django app is correctly initialized
from sentry.runner import configure
configure()


import logging
import click
import sys
import json
import glob
import pickle
import time
from pathlib import Path
from typing import List, Dict, Optional
import os
from multiprocessing import Manager

from sentry.event_manager import materialize_metadata
from sentry.eventstore.models import Event
from sentry import get_version, _get_git_revision

import sentry_sdk
sentry_sdk.init("")

from grouping_tests.groups.base import GroupNode
from grouping_tests.groups.flat import ListNode
from grouping_tests.groups.tree import TreeNode
from grouping_tests.report import HTMLReport, ProjectReport
from grouping_tests.crash import get_crash_report, dump_variants


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
@click.option("--num-workers", type=int, help="Parallelize. Default corresponds to Python multiprocessing default")
@click.option(
    "--pickle-dir",
    type=Path,
    help="If set, cache issue trees as pickles. Useful for development.")
def create_grouping_report(event_dir: Path, config: Path, report_dir: Path,
                           grouping_mode: str, events_base_url: str,
                           pickle_dir: Path, num_workers: int):
    """ Create a grouping report """

    if events_base_url is None:
        events_base_url = f"file://{event_dir.absolute()}"

    if report_dir.exists():
        LOG.error(f"Report dir {report_dir} already exists")
        sys.exit(1)

    os.makedirs(report_dir, exist_ok=True)

    if pickle_dir:
        os.makedirs(pickle_dir, exist_ok=True)

    with open(config, 'r') as config_file:
        config_dict = json.load(config_file)

    report_metadata = write_metadata(report_dir, config_dict)

    group_type = GROUP_TYPES[grouping_mode]

    t0 = time.time()

    project_ids = []
    for entry in os.scandir(event_dir):
        project_id = entry.name
        project_ids.append(project_id)

        project = None
        if pickle_dir:
            LOG.info("Project %s: Load from pickle...", project_id)
            project = load_pickle(pickle_dir, project_id)

        if project is None:
            project = generate_project_tree(
                event_dir, config_dict, group_type, entry, num_workers)
            if pickle_dir:
                store_pickle(pickle_dir, project)

        LOG.info("Project %s: Saving HTML report...", project_id)
        project.exemplar = None  # HACKish makes sure that project does not display hash, stack trace, etc.

        ProjectReport(project, report_dir, events_base_url)

        LOG.info("Project %s: Done.", project_id)

    HTMLReport(report_dir, report_metadata, project_ids)

    LOG.info("Done. Time ellapsed: %s", (time.time() - t0))


def generate_project_tree(event_dir, config, group_type, entry, num_workers):

    project_id = entry.name

    # Create a root node for all groups
    project = group_type(project_id)

    LOG.info("Project %s: Collecting filenames...", project_id)
    # iglob would be easier on memory, but we want to use the progress bar
    filenames = glob.glob(f"{entry.path}/**/*json", recursive=True)

    LOG.info("Project %s: Processing...", project_id)
    with Manager() as manager:
        with manager.Pool(num_workers) as pool:
            processor = EventProcessor(event_dir, config, project_id)
            results = pool.imap_unordered(processor, filenames)
            progress_bar = click.progressbar(results, length=len(filenames))
            with progress_bar:
                for result in progress_bar:
                    flat_hashes, hierarchical_hashes, item = result
                    project.insert(flat_hashes, hierarchical_hashes, item)

    return project


class EventProcessor:

    def __init__(self, event_dir, config, project_id):
        self._event_dir = event_dir
        self._config = config
        self._project_id = project_id
        self._seen = set()

    def __call__(self, filename):

        with open(filename, 'r') as file_:
            event_data = json.load(file_)
        event_id = event_data['event_id']
        event = Event(
            self._project_id, event_id, group_id=None, data=event_data)

        flat_hashes, hierarchical_hashes = (
            event.get_hashes(force_config=self._config))

        if not hierarchical_hashes:
            # Prevent events ending up in the project node
            hierarchical_hashes = ["NO_HASH"]

        item = extract_event_data(event)
        item['json_url'] = Path(filename).relative_to(self._event_dir)

        # Seems abundant to do this for every event, but it's faster
        # than synchronising between processes when to generate
        item['crash_report'] = get_crash_report(event)
        item['dump_variants'] = dump_variants(self._config, event)

        return flat_hashes, hierarchical_hashes, item


def extract_event_data(event: Event) -> dict:
    title, *subtitle = event.title.split(": ")

    return {
        'event_id': event.event_id,
        'title': title,
        'subtitle': ": ".join(subtitle),
        'culprit': event.culprit
    }


def write_metadata(report_dir: Path, config: dict):
    from django.utils.timezone import now
    meta = {
        'generated': str(now()),
        'cli_args': sys.argv,
        'config': config,
        'sentry_version': get_version(),
        'grouping_tests_revision': _get_git_revision(Path(__file__).parent)
    }

    with open(report_dir / "meta.json", 'w') as f:
        json.dump(meta, f, indent=4)

    return meta


def load_pickle(pickle_dir: Path, project_id: str) -> Optional[GroupNode]:
    filename = pickle_dir / f"{project_id}.pickle"
    try:
        with open(filename, 'rb') as f:
            return pickle.load(f)
    except FileNotFoundError:
        return None


def store_pickle(pickle_dir: Path, project: GroupNode):
    filename = pickle_dir / f"{project.name}.pickle"
    with open(filename, 'wb') as f:
        pickle.dump(project, file=f)


if __name__ == "__main__":
    create_grouping_report()  # pylint: disable=no-value-for-parameter
