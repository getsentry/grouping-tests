from typing import Dict, List


class GroupNode:

    def __init__(self, name: str):

        self.name = name
        self.item_count = 0
        self.items = []
        self._children: Dict[str, GroupNode] = {}

    def insert(self, path: List[str], item):
        if path:
            head, *tail = path
            self._child(head).insert(tail, item)
        else:
            self.items.append(item)
        self.item_count += 1

    def visit(self, visitor, depth=0):
        visitor(self, depth)
        for child in self._children.values():
            child.visit(visitor, depth + 1)

    def _child(self, name):
        if name not in self._children:
            child = self._children[name] = GroupNode(name)
        else:
            child = self._children[name]

        return child