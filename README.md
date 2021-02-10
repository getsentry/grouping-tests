# grouping-tests
Create &amp; visualize output of different grouping strategies

## Prerequisites

For now, run these scripts in the virtualenv of your local getsentry installation. The scripts assume you placed this repo in the same parent directory as the getsentry repo itself.


## Usage

### Persist events

Use ``store_events.py`` to write event payloads to disk. For this purpose, use ``clickhouse-client`` to select relevant events and limit the number of results, e.g.

```bash
clickhouse-client --query 'SELECT project_id, event_id FROM sentry_local LIMIT 100' \
| python store_events.py --output-dir ./events
```

