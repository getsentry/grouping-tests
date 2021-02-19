from pathlib import Path
from typing import List
import json
import os

from django.conf import settings
from django.template.loader import render_to_string

from grouping_tests.groups.base import GroupNode


# HACK: add template dir to Django settings
settings.TEMPLATES[0]['DIRS'] = (
    settings.TEMPLATES[0]['DIRS'] + [Path(__file__).parent / "templates"]
)


class HTMLReport:

    def __init__(self, parent_dir: Path, metadata, projects: List[str]):

        render_to_file("report.html", parent_dir / "index.html", {
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

        render_to_file("group-node.html", output_path, {
            'title': node_title(node),
            'subtitle': node_subtitle(node),
            'hash': node_hash(node),
            'node': node,
            'ancestors': reversed([
                ((i+1) * "../", node_title(ancestor))
                for i, ancestor in enumerate(reversed(ancestors))
            ]),
            'home': (len(ancestors) + 1) * "../",
            'descendants': self._get_descendants(node, []),  # Skip self
            'events_base_url': self._events_base_url,
        })

    @classmethod
    def _get_descendants(cls, node, ancestors):
        child_ancestors = ancestors + [node]
        return [
            (
                child,
                descendant_url(child, child_ancestors[1:]),
                cls._get_descendants(child, child_ancestors),
            )
            for child in node.children.values()
        ]

    def _html_path(self, node: GroupNode, ancestors: List[GroupNode]):
        path = [ancestor.name for ancestor in ancestors] + [node.name]

        return self._root_dir.joinpath(*path) / "index.html"


def render_to_file(template_name: str, output_path: Path, context: dict):

    html = render_to_string(template_name, context)

    os.makedirs(output_path.parent, exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(html)


def descendant_url(node, ancestors):
    return "/".join(a.name for a in ancestors + [node]) + "/index.html"


def is_project(node):
    return node.name.startswith("project_")


def node_title(node):
    if node.exemplar is None or is_project(node):
        return node.name

    return node.exemplar['title']


def node_subtitle(node):
    if node.exemplar is None or is_project(node):
        return None

    return node.exemplar['subtitle']


def node_hash(node):
    return None if is_project(node) else node.name