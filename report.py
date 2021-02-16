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

    def __init__(self, root: GroupNode, parent_dir: Path):
        self._root_dir = parent_dir
        self._current_depth = 0
        root.visit(self._visit)

    def _visit(self, node: GroupNode, ancestors: List[GroupNode]):

        output_path = self._html_path(node, ancestors)

        render_to_file("group-node.html", output_path, {
            'node': node,
            'children': node.children.values(),
            'ancestors': ancestors,
        })

    def _html_path(self, node: GroupNode, ancestors: List[GroupNode]):
        path = [ancestor.name for ancestor in ancestors] + [node.name]

        return self._root_dir.joinpath(*path) / "index.html"


def render_to_file(template_name: str, output_path: Path, context: dict):

    html = render_to_string(template_name, context)

    os.makedirs(output_path.parent, exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(html)
