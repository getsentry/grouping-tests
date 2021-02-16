from pathlib import Path
from typing import List
import os

from django.conf import settings
from django.template.loader import render_to_string

from groups.base import GroupNode


# HACK: add template dir to Django settings
settings.TEMPLATES[0]['DIRS'] = (
    settings.TEMPLATES[0]['DIRS'] + (Path(__file__).parent / "templates",)
)

class HTMLReport:

    def __init__(self, root: GroupNode, parent_dir: Path):
        self._root_dir = parent_dir
        self._current_depth = 0
        root.visit(self._visit)

    def _visit(self, node: GroupNode, ancestors: List[GroupNode]):

        html = render_to_string("group-node.html", {
            'node': node,
            'children': node.children.values(),
            'ancestors': ancestors,
        })

        output_path = self._html_path(node, ancestors)
        os.makedirs(output_path.parent, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(html)

    def _html_path(self, node: GroupNode, ancestors: List[GroupNode]):
        path = [ancestor.name for ancestor in ancestors] + [node.name]

        return self._root_dir.joinpath(*path) / "index.html"
