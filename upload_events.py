from sentry.runner import configure
configure()

import json
import time
import uuid
import click
from datetime import datetime
from pathlib import Path
from queue import Queue
from multiprocessing import cpu_count
from threading import Thread

from wipe_project import delete_groups
from sentry.models import Project, ProjectKey
from sentry.stacktraces.processing import find_stacktraces_in_data
from sentry.utils.safe import get_path, set_path
import sentry_sdk
from sentry_sdk.utils import format_timestamp
from sentry_sdk.envelope import Envelope


sentry_sdk.init("")

StopWorking = "stop_working"


@click.command()
@click.option("--file-name", required=True, type=Path, help="File/pipe name to use for reading the events")
@click.option("--dsn", type=str, help="the dsn to use, alternative to project-id or (project-slug, org-slug)")
@click.option("--project-id", type=int, help="the project id to be dumped, alternative to dsn, or (project-slug,org-slug)")
@click.option("--project-slug", type=str, help="project slug, must also use org-slug, alternatively use project-id or dsn")
@click.option("--org-slug", type=str, help="organization slug, must also use project-slug, alternatively use project-id or dsn")
@click.option("--network-threads", default=64, help="How many threads to use for sending")
@click.option("--wipe-project/--leave-project", default=False, type=bool, help="remove all existing messages from the project before import")
@click.option("--event-sleep", default=0, help="How many milliseconds to sleep between events")
def upload_events(file_name: Path, dsn: str, project_id: int, project_slug: str, org_slug: str, wipe_project: bool, event_sleep: int, network_threads: int):
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

        events = _parse_lines(input_stream)

        header = next(events)

        num_events = header.get("max_events")
        if num_events is None:
            num_events = 1000  # just a guess
            print("Uploading events....")
        else:
            print(f"Uploading {num_events} events....")

        q = Queue(network_threads * 2 + 2)  # large enough so that workers do not wait

        workers = []

        for i in range(network_threads):
            t = Thread(target=worker_loop, args=(dsn, q))
            t.start()
            workers.append(t)

        with click.progressbar(events, length=num_events) as events2:
            last_sleep = time.time()
            event_count = 0
            skip_count = 0

            for event in events2:

                if skip_event(event):
                    skip_count += 1
                    continue

                event.pop('project', None)
                if get_path(event, 'exception', 'values', 0, 'stacktrace', 'frames'):
                    event.pop('threads', None)
                elif (
                    get_path(event, "logentry", "formatted") and
                    get_path(event, "threads", "values") and
                    get_path(event, "platform") == "cocoa"
                ):
                    # Deal with Cocoa 6 NSError events that are sent as
                    # stacktrace + logentry
                    # we assume all of those kinds of events are NSError which
                    # is not really true, only most of the time
                    message = event.pop("logentry")['formatted']

                    threads = event.pop("threads")['values']
                    thread = next((x for x in threads if x.get('current')), threads[0])

                    event['exception'] = {
                        "values": [
                            {
                                "type": message,
                                "mechanism": {
                                    "type": "NSError",
                                    "value": "<converted from sentry-cocoa 6>",
                                    "meta": {
                                        "ns_error": {
                                            # Not 100% correct, domain is a
                                            # substring of message but it
                                            # should group about the same as we
                                            # always group by (domain, code)
                                            "domain": message,
                                            "code": 2,
                                        }
                                    }
                                },
                                "stacktrace": thread.get("stacktrace"),
                            }
                        ]
                    }
                elif get_path(event, "platform") == "cocoa" and get_path(event, "exception", "values", 0, "mechanism", "meta", "ns_error") and not get_path(event, "exception", "values", 0, "stacktrace") and get_path(event, "threads", "values"):
                    # Event the Cocoa 6 events are "crappy" because the
                    # exception contains no stacktrace, instead the thread does
                    #
                    # TODO(markus): Relay should've normalized this
                    threads = event.pop("threads")['values']
                    thread = next((x for x in threads if x.get('current')), threads[0])
                    if thread and thread.get("stacktrace"):
                        event['exception']['values'][0]['stacktrace'] = thread["stacktrace"]

                event.pop('debug_meta', None)
                event.pop('_ref', None)
                event.pop('_ref_version', None)
                event.pop('location', None)
                event.pop('title', None)

                # make sure the event does not go through minidump processing,
                # otherwise we get weird errors in the pipeline we have to
                # ignore
                exceptions = get_path(event, "exception", "values", filter=True)
                if exceptions:
                    mechanism = get_path(exceptions, 0, "mechanism", "type")

                    if mechanism:
                        set_path(exceptions, 0, "mechanism", "type", value=f"{mechanism}_disabled")

                for stacktrace_info in find_stacktraces_in_data(event):
                    for frame in get_path(stacktrace_info.stacktrace, "frames", filter=True, default=()) or ():
                        orig_in_app = get_path(frame, "data", "orig_in_app")
                        if orig_in_app is not None:
                            frame["in_app"] = None if orig_in_app == -1 else bool(orig_in_app)

                event_id = event.pop('event_id', None)
                event['tags'] = {"orig_event_id": event_id}
                event['event_id'] = event_id = str(uuid.uuid4().hex).replace("-", "")

                envelope = Envelope(
                    headers={
                        "event_id": event_id,
                        "sent_at": format_timestamp(datetime.utcnow())
                    }
                )

                envelope.add_event(event)

                q.put(envelope)

                event_count += 1

                if event_sleep and time.time() - last_sleep > 10 and event_count > 100:
                    time.sleep(event_count * event_sleep / 1000.0)
                    last_sleep = time.time()
                    event_count = 0

        # send end of work signals to the workers, put a few more to be sure
        for i in range(network_threads + 2):
            q.put(StopWorking)

        # wait for workers to finish
        for worker in workers:
            worker.join()

        if skip_count:
            print(f"Skipped {skip_count} event(s).")

        print(f"Done. Elapsed time is {time.time() - now} secs.")

def _parse_lines(input_stream):
    for line in input_stream:
        line = line.strip()
        if line == "---" or not line:
            continue

        yield json.loads(line)

def worker_loop(dsn, queue):
    client = sentry_sdk.Client(dsn)
    while True:
        msg = queue.get()
        if msg == StopWorking:
            break

        client.transport._send_envelope(msg)

    if client.transport._disabled_until:
        print(f"WARNING: Hit rate limits: {client.transport._disabled_until}")


def skip_event(event: dict) -> bool:
    """ Returns True if the event should not be uploaded """
    fingerprint = event.get("fingerprint")
    # We only want to skip fingerprints which do not include "{{ default }}"
    if fingerprint and "{{ default }}" not in fingerprint:
        return True

    return False


if __name__ == "__main__":
    upload_events()  # pylint: disable=no-value-for-parameter
