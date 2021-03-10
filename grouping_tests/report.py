from pathlib import Path
from typing import List
import json
import logging
import os
import shutil

import click
from django.conf import settings
from django.template.loader import render_to_string

from grouping_tests.groups.base import GroupNode


LOG = logging.getLogger(__name__)


# HACK: add template dir to Django settings
settings.TEMPLATES[0]['DIRS'] = (
    list(settings.TEMPLATES[0]['DIRS']) + [Path(__file__).parent / "templates"]
)


class HTMLReport:

    def __init__(self, parent_dir: Path, metadata, projects: List[str]):

        self._copy_static_files(parent_dir)

        _render_to_file("report.html", parent_dir / "index.html", {
            'projects': sorted(projects),
            'metadata': json.dumps(metadata, indent=4),
        })

    @staticmethod
    def _copy_static_files(parent_dir: Path):
        src = Path(__file__).parent / "static"
        dst = parent_dir / "static"

        shutil.copytree(src, dst)


class ProjectReport:

    def __init__(self, root: GroupNode, parent_dir: Path, events_base_url: str):
        self._root_dir = parent_dir
        self._events_base_url = events_base_url
        self._current_depth = 0

        # Write grouping variants to disk for each event
        LOG.info("Project %s: Writing event data...", root.name)
        with click.progressbar(length=root.total_item_count) as progress_bar:
            for node, ancestors in root.nodes():
                self._write_event_data(node, ancestors, progress_bar.update)

        # Create HTML page for each node
        LOG.info("Project %s: Writing HTML report...", root.name)
        with click.progressbar(length=root.total_item_count) as progress_bar:
            for node, ancestors in root.nodes():
                self._render_node(node, ancestors, progress_bar.update)

    def _render_node(self, node: GroupNode, ancestors: List[GroupNode], update_fn):
        output_path = self._html_path(node, ancestors)

        _render_to_file("group-node.html", output_path, {
            'title': _node_title(node),
            'subtitle': _node_subtitle(node),
            'hash': _node_hash(node),
            'node': node,
            'ancestors': reversed([
                ((i+1) * "../", _node_title(ancestor), _breadcrumb(ancestor))
                for i, ancestor in enumerate(reversed(ancestors))
            ]),
            'home': (len(ancestors) + 1) * "../",
            'descendants': _get_descendants(node, []),  # Skip self
            'events_base_url': self._events_base_url,
            'tree_chart_data': json.dumps(_node_to_d3(node)),
            'event_iterator': UpdatingIterator(node.items, update_fn)
        })

    def _output_path(self, node: GroupNode, ancestors: List[GroupNode]):
        path = [ancestor.name for ancestor in ancestors] + [node.name]

        return self._root_dir.joinpath(*path)

    def _html_path(self, node: GroupNode, ancestors: List[GroupNode]):
        return self._output_path(node, ancestors) / "index.html"

    def _rel_url(self, node: GroupNode, ancestors: List[GroupNode]):
        path = [ancestor.name for ancestor in ancestors] + [node.name]

        return "/".join(path)

    def _write_event_data(self, node, ancestors, update_fn):
        # Store variant dump on disk, but only if it's different from the
        # exemplar's dump
        exemplar_variants = (node.exemplar or {}).get('dump_variants')
        event_data_target_dir = self._output_path(node, ancestors) / "event_data"
        os.makedirs(event_data_target_dir, exist_ok=False)
        for event in node.items:
            dump_variants = event.get('dump_variants')
            if event == node.exemplar or dump_variants != exemplar_variants:
                filename = f"{event['event_id']}-dump-variants.txt"
                event['dump_variants_url'] = (
                    f"{self._rel_url(node, ancestors)}/event_data/{filename}"
                )
                with open(event_data_target_dir / filename, 'w') as f:
                    f.write(f"{dump_variants}")
            else:
                # Refer to same variant as exemplar
                # NOTE: assumes that exemplar.dump_variants_url is set earlier
                event['dump_variants_url'] = node.exemplar['dump_variants_url']
            update_fn(1)


def _get_descendants(node, ancestors):
    child_ancestors = ancestors + [node]
    children = [
        (
            child,
            _descendant_url(child, child_ancestors[1:]),
            _get_descendants(child, child_ancestors),
        )
        for child in node.children.values()
    ]

    children.sort(key= lambda t: _node_title(t[0]))

    return children


def _render_to_file(template_name: str, output_path: Path, context: dict):

    html = render_to_string(template_name, context)

    os.makedirs(output_path.parent, exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(html)


def _descendant_url(node, ancestors):
    return "/".join(a.name for a in ancestors + [node]) + "/index.html"


def _is_project(node):
    return node.name.startswith("project_")


def _node_title(node):
    return node.exemplar['title'] if node.exemplar else node.name


def _node_subtitle(node):
    return node.exemplar and node.exemplar['subtitle']


def _breadcrumb(node):
    if node.children and node.label:
        # Use tree label for intermediate nodes
        return node.label

    return _node_title(node)


def _node_hash(node):
    return None if _is_project(node) else node.name


def _get_field(node, name):
    return node.exemplar and node.exemplar.get(name)


def _node_to_d3(node: GroupNode, ancestors=None) -> dict:
    """ Convert node to d3 format for easy chart rendering """

    if ancestors is None:
        ancestors = []

    children = [
        _node_to_d3(child, ancestors + [node])
        for child in node.children.values()
    ]
    children.sort(key=lambda d: d['name'])

    return {
        "name": node.label or _node_title(node),
        "href": _descendant_url(node, ancestors[1:]) if ancestors else None,
        "item_count": node.item_count,
        "children": children,
    }


class UpdatingIterator:

    """ Used to connect progress bar with django template """

    def __init__(self, items, update_fn):
        self._items = items
        self._update_fn = update_fn

    def __iter__(self):
        update_fn = self._update_fn
        for item in self._items:
            update_fn(1)
            yield item

    def __len__(self):
        """ Needed by django template """
        return len(self._items)
