# grouping-tests
Create &amp; visualize output of different grouping strategies

## Prerequisites

For now, run these scripts in the virtualenv of your local sentry installation.

This requires that you checkout sentry's [hierarchical group hashes](https://github.com/getsentry/sentry/pull/23861) branch.

## Usage

### Persist events

Use ``store_events.py`` to write event payloads to disk. For this purpose, use ``clickhouse-client`` to select relevant events and limit the number of results, e.g.

```bash
clickhouse-client --query 'SELECT project_id, event_id FROM sentry_local LIMIT 100' \
| python store_events.py --output-dir ./events
```

### Create grouping report (under development)

Applies a grouping strategy and creates the corresponding report. In addition to the config file, you must choose from either ``flat`` or ``tree`` grouping mode on the command line:

```bash
python create_grouping_report.py \
    --events-dir ./events \
    --config ./config.json \
    --report-dir ./report_$(date) \
    --grouping-mode tree
```

A summary of the grouping is printed to stdout. ``--report-dir`` is currently ignored.

Example config:

```json
{
    "id": "newstyle:2019-10-29"
}
```
