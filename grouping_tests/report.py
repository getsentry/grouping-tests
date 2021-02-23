from pathlib import Path
from typing import List
import json
import os
from difflib import unified_diff

from django.conf import settings
from django.template.loader import render_to_string

from grouping_tests.groups.base import GroupNode


# HACK: add template dir to Django settings
settings.TEMPLATES[0]['DIRS'] = (
    settings.TEMPLATES[0]['DIRS'] + [Path(__file__).parent / "templates"]
)


class HTMLReport:

    def __init__(self, parent_dir: Path, metadata, projects: List[str]):

        _render_to_file("report.html", parent_dir / "index.html", {
            'projects': sorted(projects),
            'metadata': json.dumps(metadata, indent=4)
        })


class ProjectReport:

    def __init__(self, root: GroupNode, parent_dir: Path, events_base_url: str):
        self._root_dir = parent_dir
        self._events_base_url = events_base_url
        self._current_depth = 0

        root.visit(self._render_node)  # Renders all nodes

    def _render_node(self, node: GroupNode, ancestors: List[GroupNode]):

        output_path = self._html_path(node, ancestors)

        _render_to_file("group-node.html", output_path, {
            'title': _node_title(node),
            'subtitle': _node_subtitle(node),
            'hash': _node_hash(node),
            'node': node,
            'ancestors': reversed([
                ((i+1) * "../", _node_title(ancestor))
                for i, ancestor in enumerate(reversed(ancestors))
            ]),
            'home': (len(ancestors) + 1) * "../",
            'descendants': _get_descendants(node, []),  # Skip self
            'events_base_url': self._events_base_url,
        })

    def _html_path(self, node: GroupNode, ancestors: List[GroupNode]):
        path = [ancestor.name for ancestor in ancestors] + [node.name]

        return self._root_dir.joinpath(*path) / "index.html"


def _get_descendants(node, ancestors):
    child_ancestors = ancestors + [node]
    return [
        (
            child,
            _descendant_url(child, child_ancestors[1:]),
            _node_diff(node, child),
            _get_descendants(child, child_ancestors),
        )
        for child in node.children.values()
    ]


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


def _node_hash(node):
    return None if _is_project(node) else node.name


def _get_field(node, name):
    return node.exemplar and node.exemplar.get(name)


def _node_diff(from_: GroupNode, to: GroupNode) -> str:
    """ What sets this node apart from the other node """
    dv1 = _get_field(from_, 'dump_variants')
    dv2 = _get_field(to, 'dump_variants')

    if dv1 and dv2:
        return "\n".join(unified_diff(
                dv1.splitlines(1),
                dv2.splitlines(1)
            )
        )

    return ""

