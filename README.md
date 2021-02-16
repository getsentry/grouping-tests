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

### Create grouping report

Under development.
The current version builds a tree from the hashes returned by the grouping config and prints it to stdout. ``--report-dir`` is currently ignored.

```bash
python create_grouping_report.py \
    --events-dir ./events \
    --config ./config.json \
    --report-dir ./report_$(date) \
    --grouping-mode tree
```

Example config:

```json
{
    "id": "legacy:2019-03-12"
}
```
