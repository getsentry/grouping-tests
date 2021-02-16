from typing import Dict, List


class EventGroup:

    """ Group of events. Subclasses differ in the way they insert / merge events """

    def __init__(self, name: str):

        self.name = name
        self.item_count = 0
        self.items = []
        self._children: Dict[str, EventGroup] = {}

    def insert(self, flat_hashes: List[str], hierarchical_hashes: List[str], item):
        raise NotImplementedError

    def visit(self, visitor, depth=0):
        visitor(self, depth)
        for child in self._children.values():
            child.visit(visitor, depth + 1)

    def _child(self, name):
        if name not in self._children:
            child = self._children[name] = self.__class__(name)
        else:
            child = self._children[name]

        return child

