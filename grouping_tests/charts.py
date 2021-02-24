from typing import List, Dict

from grouping_tests.groups.base import GroupNode


def node_to_plotly(node: GroupNode) -> dict:
    """ Transform node + children to plotly format """

    data = {
        "ids": [],
        "labels": [],
        "parents": [],
        "values": [],
    }

    def visitor(node: GroupNode, ancestors):
        data['ids'].append(node.name)
        data['labels'].append(_title(node))
        data['parents'].append(ancestors[-1].name if ancestors else "")
        data['values'].append(node.item_count)

    node.visit(visitor)

    return data


def _title(node: GroupNode) -> str:
    if node.exemplar:
        short_name = node.name[:8]
        return f"{node.exemplar['title']} {short_name}"

    return node.name