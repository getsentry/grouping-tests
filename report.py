from pathlib import Path
from typing import List
import os

from django.template import Context, Template

from groups.base import GroupNode


GROUP_NODE_TEMPLATE = Template("""

    <h1>{{ node.name }}</h1>

    {% if ancestors %}
        <a href="../index.html">⇧ Up</a>
    {% endif %}

    {% if children %}
        <h2>Children</h2>
        <ul>
            {% for child in children %}
                <li>
                    <a href="{{ child.name }}/index.html">{{ child.name }}</a>
                </li>
            {% endfor %}

        </ul>
    {% endif %}

    {% if node.items %}
        <h2>Events</h2>
        <ul>
            {% for event in node.items %}
                <li>
                    {{ event.metadata.title }}
                </li>
            {% endfor %}
        </ul>
    {% endif %}
""")


class HTMLReport:

    def __init__(self, root: GroupNode, parent_dir: Path):
        self._root_dir = parent_dir
        self._current_depth = 0
        root.visit(self._visit)

    def _visit(self, node: GroupNode, ancestors: List[GroupNode]):

        html = GROUP_NODE_TEMPLATE.render(Context({
            'node': node,
            'children': node.children.values(),
            'ancestors': ancestors,
        }))

        output_path = self._html_path(node, ancestors)
        os.makedirs(output_path.parent, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(html)

    def _html_path(self, node: GroupNode, ancestors: List[GroupNode]):
        path = [ancestor.name for ancestor in ancestors] + [node.name]

        return self._root_dir.joinpath(*path) / "index.html"
