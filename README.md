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

### Create grouping report

Applies a grouping strategy and creates the corresponding report.

If the resulting HTML report will be served via HTTP, make sure that the ``events``
directory is also available, and pass its URL via ``--events-base-url``.

```bash
python create_grouping_report.py \
    --events-dir ./events \
    --config ./config.json \
    --report-dir ./report_$(date) \
    --events-base-url http://example.com/events  # optional
```

Example config:

```json
{
    "id": "mobile:2021-02-12"
}
```

### Serving the grouping report

The report loads some event data lazily via AJAX. For this to work, you need to
serve the report from a web server, e.g.

```bash
python3 -m http.server
```

### TODO

#### Nice to haves

- [ ] Diff anything in node compare (apple crash report, stack trace variants)
