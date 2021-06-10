from sentry.runner import configure
configure()

from yaml import load_all
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

import time
import click
from pathlib import Path
from queue import Queue
from multiprocessing import cpu_count
from threading import Thread

from wipe_project import delete_groups
from sentry.models import Project, ProjectKey
import sentry_sdk


sentry_sdk.init("")

StopWorking = "stop_working"


@click.command()
@click.option("--file-name", required=True, type=Path, help="File/pipe name to use for reading the events")
@click.option("--dsn", type=str, help="the dsn to use, alternative to project-id or (project-slug, org-slug)")
@click.option("--project-id", type=int, help="the project id to be dumped, alternative to dsn, or (project-slug,org-slug)")
@click.option("--project-slug", type=str, help="project slug, must also use org-slug, alternatively use project-id or dsn")
@click.option("--org-slug", type=str, help="organization slug, must also use project-slug, alternatively use project-id or dsn")
@click.option("--expire-days", default=0, type=int, help="sets timestamp in the past to influence retention")
@click.option("--wipe-project/--leave-project", default=False, type=bool, help="remove all existing messages from the project before import")
def upload_events(file_name: Path, dsn: str, project_id: int, project_slug: str, org_slug: str, expire_days: int, wipe_project: bool):
    """
    Reads events from a file (or named pipe) containing a multi doc yaml and sends them to a project.

    Optionally it wipes the project of all messages before starting to send.
    """
    if dsn is None:
        if project_id is not None:
            project = Project.objects.get(id=project_id)
        else:
            project = Project.objects.get(organization__slug=org_slug, slug=project_slug)
            project_id = project.id
        project_key = ProjectKey.get_default(project)
        dsn = project_key.dsn_public
    else:
        project_id = int(dsn.split("/")[-1])

    if wipe_project:
        delete_groups(project_id)

    with open(file_name, "rt") as input_stream:
        now = time.time()

        events = load_all(input_stream, Loader=Loader)

        header = next(events)

        num_events = header.get("max_events")
        if num_events is None:
            num_events = 1000  # just a guess
            print("Uploading events....")
        else:
            print(f"Uploading {num_events} events....")

        num_workers = cpu_count() * 2  # empirically 2* num_cpu seems to give the fastest performance
        q = Queue(num_workers * 2 + 2)  # large enough so that workers do not wait

        workers = []

        for i in range(num_workers):
            t = Thread(target=worker_loop, args=(dsn, q))
            t.start()
            workers.append(t)

        with click.progressbar(events, length=num_events) as events2:
            for event in events2:
                event.pop('event_id', None)
                event.pop('project', None)
                if expire_days:
                    # Snuba retention is timestamp-based.
                    event['timestamp'] = now - ((expire_days - 90) * 3600 * 24)
                else:
                    event.pop('timestamp', None)
                event.pop('threads', None)
                event.pop('debug_meta', None)
                q.put(event)

        # send end of work signals to the workers, put a few more to be sure
        for i in range(num_workers + 2):
            q.put(StopWorking)

        # wait for workers to finish
        for worker in workers:
            worker.join()

        print(f"Done. Elapsed time is {time.time() - now} secs.")

def worker_loop(dsn, queue):
    client = sentry_sdk.Client(dsn)
    while True:
        msg = queue.get()
        if msg == StopWorking:
            break
        client.transport._send_event(msg)


if __name__ == "__main__":
    upload_events()  # pylint: disable=no-value-for-parameter
