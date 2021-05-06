from sentry.runner import configure
configure()

import sentry_sdk
sentry_sdk.init("")

import glob
import time
import json
import click
from pathlib import Path

@click.command()
@click.option("--event-dir", required=True, type=Path, help="created using store_events.py")
@click.option("--dsn", required=True)
@click.option("--expire-days", default=0, type=int, help="sets timestamp in the past to influence retention")
def upload_events(event_dir, dsn, expire_days):
    client = sentry_sdk.Client(dsn)

    now = time.time()

    filenames = glob.glob(f"{event_dir}/**/*json", recursive=True)

    for filename in click.progressbar(filenames):
        with open(filename) as f:
            event = json.load(f)
            event.pop('event_id', None)
            event.pop('project', None)
            if expire_days:
                # Snuba retention is timestamp-based.
                event['timestamp'] = now - ((expire_days - 90) * 3600 * 24)
            else:
                event.pop('timestamp', None)
            event.pop('threads', None)
            event.pop('debug_meta', None)

            client.transport._send_event(event)


    print(f"Done. Elapsed time is {time.time() - now} secs.")


if __name__ == "__main__":
    upload_events()  # pylint: disable=no-value-for-parameter
