# pylint: disable=wrong-import-position
# pylint: disable=wrong-import-order
# pylint: disable=ungrouped-imports
# prelude of careful imports so django app is correctly initialized
import os

from sentry.runner import configure
configure()

from sentry.models import Project
from sentry import eventstore
import json
from pathlib import Path
import click

import sentry_sdk
sentry_sdk.init("")

@click.command()
@click.option("--project-id", type=int, help="The project numeric Id, an alternative to project slug")
@click.option("--org-slug", type=str, help="The organization slug, an alternative to project id, if used must also provide project-slug")
@click.option("--project-slug", type=str, help="The project slug, an alternative to project id, if used must also provide org-slug")
@click.option("--file-name", required=True, type=Path, help="File/pipe name to use for dumping the events")
@click.option("--max-events", type=int, default="1000", help="How many events to import")
@click.option("--use-pipe/--use-file", type=bool, default=True, help="uses a named pipe instead of a normal file")
def dump_events( project_id: int, org_slug: str, project_slug: str, file_name:Path, max_events:int, use_pipe):
    """
    Dumps events as a yaml multi doc file/stream

    Usage example:
        python dump_events --project_id 11 --max-events 500 --file-name out.yml

    """
    if file_name.exists():
        file_name.unlink()

    if use_pipe:
        os.mkfifo(file_name)

    if project_id is None:
        project = Project.objects.get(organization__slug=org_slug, slug=project_slug)
        project_id = project.id

    with open(file_name,"wt") as output_file:
        event_filter = eventstore.Filter(project_ids=[project_id])

        print("Getting events....")

        events=_get_events(event_filter, max_events=max_events)

        # write a header with the number of events (so we can support progress bars downstream)
        _write_doc_separator(output_file)
        json.dump({"max_events": max_events},output_file, separators=(',',':'))

        print(f"# Dumping {max_events} events...")
        with click.progressbar(events, length=max_events) as events:
            for event in events:
                _dump_object(event, output_file)


def _get_events(event_filter, max_events):
    from sentry.utils.query import celery_run_batch_query

    state = None

    offset = 0

    while offset < max_events:
        state, events = celery_run_batch_query(event_filter, min(500, max_events - offset), "garbage.markus.dump-events", state=state)
        offset += len(events)
        yield from events


def _write_doc_separator(file):
    """"""
    file.write("\n---\n")


def _dump_object(event, output_file):
    event_data = dict(event.data)
    _write_doc_separator(output_file)
    json.dump(event_data, output_file, separators=(',',':'))


if __name__ == "__main__":
    dump_events()  # pylint: disable=no-value-for-parameter
