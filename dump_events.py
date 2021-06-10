# pylint: disable=wrong-import-position
# pylint: disable=wrong-import-order
# pylint: disable=ungrouped-imports
# prelude of careful imports so django app is correctly initialized
import os

from sentry.runner import configure
configure()

import pytz
import json
from pathlib import Path
import datetime
import concurrent.futures
from dateutil.parser import parse as parse_date

import click

from sentry.models import Project
from sentry.eventstore.models import Event
from sentry import nodestore
from sentry.utils import snuba

from snuba_sdk.conditions import Condition, Op, Or
from snuba_sdk.orderby import Direction, OrderBy
from snuba_sdk.query import Column, Entity, Function, Query

import sentry_sdk
sentry_sdk.init("")

@click.command()
@click.option("--project-id", type=int, help="The project numeric Id, an alternative to project slug")
@click.option("--org-slug", type=str, help="The organization slug, an alternative to project id, if used must also provide project-slug")
@click.option("--project-slug", type=str, help="The project slug, an alternative to project id, if used must also provide org-slug")
@click.option("--file-name", required=True, type=Path, help="File/pipe name to use for dumping the events")
@click.option("--max-events", type=int, default="1000", help="How many events to import")
@click.option("--use-pipe/--use-file", type=bool, default=True, help="uses a named pipe instead of a normal file")
@click.option("--batch-size", type=int, default=200, help="How many events to fetch at once from Snuba and nodestore.")
@click.option("--network-threads", default=64, help="How many threads to spawn for fetching")
def dump_events( project_id: int, org_slug: str, project_slug: str, file_name:Path, max_events:int, use_pipe, batch_size: int, network_threads: int):
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
        print("Getting events....")

        events_estimate = min(snuba.raw_snql_query(_get_query(project_id, []), referrer="garbage.markus.get-estimate")['data'][0]['count'], max_events)

        chunks = _copy_events(project_id, max_events, output_file, batch_size, network_threads)

        # write a header with the number of events (so we can support progress bars downstream)
        _write_doc_separator(output_file)
        json.dump({"max_events": events_estimate},output_file, separators=(',',':'))

        print(f"# Dumping roughly {events_estimate} events...")
        with click.progressbar(chunks, length=max_events) as chunks:
            for _ in chunks:
                pass



def _get_query(project_id, where):
    now = datetime.datetime.now()
    where.append(
        # GDPR
        Condition(Column("timestamp"), Op.GTE, now - datetime.timedelta(days=30))
    )

    where.append(Condition(Column("timestamp"), Op.LT, now))
    where.append(Condition(Column("project_id"), Op.EQ, project_id))

    query = (
        Query("events", Entity("events"))
        .set_select([
            Function("uniqExact", [Column("primary_hash")], "count"),
        ])
        .set_where(where)
    )

    return query


def _load_events(project_id, max_events, output_file, batch_size):
    from sentry.utils.query import celery_run_batch_query

    state = None

    now = datetime.datetime.now()

    num_events = 0

    while True:
        where = [Condition(Column("timestamp"), Op.LTE, now)]

        query = _get_query(project_id, where).set_select([
            Function("argMax", [Column("event_id"), Column("timestamp")], "last_event_id"),
            Function("max", [Column("timestamp")], "last_timestamp")
        ]) \
            .set_limit(min(batch_size, max_events - num_events)) \
            .set_offset(num_events) \
            .set_orderby([OrderBy(Column("last_timestamp"), Direction.DESC), OrderBy(Column("last_event_id"), Direction.DESC)]) \
            .set_groupby([Column("primary_hash")])

        result = snuba.raw_snql_query(query, referrer="garbage.markus.dump-events")['data']
        if not result:
            break

        num_events += len(result)

        for row in result:
            yield row['last_event_id']

    print(f"# Dumped {num_events} events.")


def _copy_events(project_id, max_events, output_file, batch_size, max_workers):

    def _load(event_id):
        node_id = Event.generate_node_id(project_id, event_id)

        value = nodestore.backend._get_bytes(node_id)
        # copied from nodestore impl
        event_data_raw = next(iter(value.splitlines()))

        return event_data_raw

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        batch = []
        for event_id in _load_events(project_id, max_events, output_file, batch_size):
            batch.append(event_id)
            yield

            if len(batch) >= batch_size:
                futures = [executor.submit(_load, event_id) for event_id in batch]

                for future in concurrent.futures.as_completed(futures):
                    event_data_raw = future.result()
                    _write_doc_separator(output_file)
                    output_file.write(event_data_raw.decode("utf8"))

                batch = []



def _write_doc_separator(file):
    """"""
    file.write("\n---\n")


if __name__ == "__main__":
    dump_events()  # pylint: disable=no-value-for-parameter
