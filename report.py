from pathlib import Path
from typing import List
import json
import os

from django.conf import settings
from django.template.loader import render_to_string

from groups.base import GroupNode


# HACK: add template dir to Django settings
settings.TEMPLATES[0]['DIRS'] = (
    settings.TEMPLATES[0]['DIRS'] + (Path(__file__).parent / "templates",)
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
        root.visit(self._visit)

    def _visit(self, node: GroupNode, ancestors: List[GroupNode]):

        # Every page contains a view of the descendants, so visit children again:
        descendants = []
        def collect_descendants(node, ancestors):
            ancestors = ancestors[1:]  # Skip self
            descendants.append((
                3*len(ancestors), descendant_url(node, ancestors), node
            ))
        node.visit(collect_descendants)

        output_path = self._html_path(node, ancestors)

        is_project = node.name.startswith("project_")

        render_to_file("group-node.html", output_path, {
            'title': node.name if is_project else node.exemplar['title'],
            'subtitle': None if is_project else node.exemplar['subtitle'],
            'node': node,
            'ancestors': reversed([
                ((i+1) * "../", ancestor)
                for i, ancestor in enumerate(reversed(ancestors))
            ]),
            'home': (len(ancestors) + 1) * "../",
            'descendants': descendants[1:],  # Skip self
            'events_base_url': self._events_base_url,
        })

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