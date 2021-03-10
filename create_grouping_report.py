# pylint: disable=wrong-import-position
# pylint: disable=wrong-import-order
# pylint: disable=ungrouped-imports
# prelude of careful imports so django app is correctly initialized
import os
os.environ['SENTRY_SKIP_SERVICE_VALIDATION'] = "yes"
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
from typing import List, Optional
from multiprocessing import Manager

from django.utils.timezone import now
from sentry.eventstore.models import Event
from sentry import get_version, _get_git_revision
from sentry.grouping.api import get_default_enhancements
from sentry.grouping.variants import BaseVariant, ComponentVariant

import sentry_sdk
sentry_sdk.init("")

from grouping_tests.groups.base import GroupNode, HashData
from grouping_tests.report import HTMLReport, ProjectReport
from grouping_tests.crash import get_crash_report, dump_variants, get_stacktrace_render


LOG = logging.getLogger(__name__)


@click.command()
@click.option("--event-dir", required=True, type=Path, help="created using store_events.py")
@click.option("--config", "-c", required=True, type=Path, multiple=True,
              help="Grouping config. Multiple will be merged left to right.")
@click.option("--report-dir", required=True, type=Path, help="output directory")
@click.option("--events-base-url", type=str,
              help="Base URL for JSON links. Defaults to --event-dir")
@click.option("--num-workers", type=int,
              help="Parallelize. Default corresponds to Python multiprocessing default")
@click.option(
    "--pickle-dir",
    type=Path,
    help="If set, cache issue trees as pickles. Useful for development.")
def create_grouping_report(event_dir: Path, config: List[Path], report_dir: Path,
                           events_base_url: str, pickle_dir: Path, num_workers: int):
    """ Create a grouping report """

    if events_base_url is None:
        events_base_url = f"file://{event_dir.absolute()}"

    if report_dir.exists():
        LOG.error("Report dir %s already exists", report_dir)
        sys.exit(1)

    os.makedirs(report_dir, exist_ok=True)

    if pickle_dir:
        os.makedirs(pickle_dir, exist_ok=True)

    config_dict = _default_config()
    for config_path in config:
        with open(config_path, 'r') as config_file:
            config_dict.update(**json.load(config_file))

    report_metadata = write_metadata(report_dir, config_dict)

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
                event_dir, config_dict, entry, num_workers)
            if pickle_dir:
                store_pickle(pickle_dir, project)

        # HACKish makes sure that project does not display hash, stack trace, etc.
        project.exemplar = None

        ProjectReport(project, report_dir, events_base_url)

        LOG.info("Project %s: Done.", project_id)

    HTMLReport(report_dir, report_metadata, project_ids)

    LOG.info("Done. Time ellapsed: %s", (time.time() - t0))


def generate_project_tree(event_dir, config, entry, num_workers):

    project_id = entry.name

    # Create a root node for all groups
    project = GroupNode(project_id, None)

    LOG.info("Project %s: Collecting filenames...", project_id)
    # iglob would be easier on memory, but we want to use the progress bar
    filenames = glob.glob(f"{entry.path}/**/*json", recursive=True)

    LOG.info("Project %s: Building issue tree...", project_id)
    with Manager() as manager:
        with manager.Pool(num_workers) as pool:
            processor = EventProcessor(event_dir, config, project_id)
            results = map_fn(pool, num_workers)(processor, filenames)
            progress_bar = click.progressbar(results, length=len(filenames))
            with progress_bar:
                for result in progress_bar:
                    if result is not None:
                        flat, hierarchical, item = result
                        if hierarchical:
                            project.insert_hierarchical(hierarchical, item)
                        else:
                            flat = flat or [HashData("NO_HASH", None)]
                            project.insert_flat(flat, item)

    return project


def map_fn(pool, num_workers):
    if num_workers == 1:
        # Keep everything in this thread, useful for debugging
        return map

    return pool.imap_unordered


class EventProcessor:

    def __init__(self, event_dir, config, project_id):
        self._event_dir = event_dir
        self._config = config
        self._project_id = project_id
        self._seen = set()

    def __call__(self, filename):
        try:
            return self._process(filename)
        except Exception as e:
            LOG.warning("Exception occured while processing event %s", filename)
            LOG.exception(e)

    def _process(self, filename):
        with open(filename, 'r') as file_:
            event_data = json.load(file_)
        event_id = event_data['event_id']
        event = Event(
            self._project_id, event_id, group_id=None, data=event_data)

        flat_variants, hierarchical_variants = (
            event.get_sorted_grouping_variants(force_config=self._config)
        )

        flat = self._get_hashes(flat_variants)
        hierarchical = self._get_hashes(hierarchical_variants)

        item = extract_event_data(event)
        item['json_url'] = Path(filename).relative_to(self._event_dir)

        # Seems abundant to do this for every event, but it's faster
        # than synchronising between processes when to generate
        item['crash_report'] = get_crash_report(event)
        item['stacktrace_render'] = get_stacktrace_render(event)
        item['dump_variants'] = dump_variants(self._config, event)

        return flat, hierarchical, item

    @classmethod
    def _get_hashes(cls, variants: List[BaseVariant]) -> List[HashData]:
        """ Get hash and label for each variant and filter out None hashes """
        pairs = (
            (variant.get_hash(), cls._get_label(variant)) for variant in variants
        )
        return [
            HashData(hash_, label) for hash_, label in pairs
            if hash_ is not None
        ]

    @staticmethod
    def _get_label(variant: BaseVariant):
        return variant.component.tree_label if isinstance(variant, ComponentVariant) else None


def extract_event_data(event: Event) -> dict:
    title, *tail = event.title.split(": ", 1)

    subtitle = tail[0] if tail else event.data.get('metadata', {}).get('value')

    return {
        'event_id': event.event_id,
        'title': title,
        'subtitle': subtitle,
        'culprit': event.culprit
    }


def write_metadata(report_dir: Path, config: dict):
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


def _default_config() -> dict:
    return {'enhancements': get_default_enhancements()}


if __name__ == "__main__":
    create_grouping_report()  # pylint: disable=no-value-for-parameter
