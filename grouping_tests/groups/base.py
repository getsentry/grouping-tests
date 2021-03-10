from collections import namedtuple
from typing import Any, Dict, List


HashData = namedtuple('HashData', ('hash', 'label'))


class GroupNode:

    """ Group of events. Subclasses differ in the way they insert / merge events """

    def __init__(self, name: str, label: str):

        self.name = name
        self.label = label

        self.total_item_count = 0  # Sum of items in self + descendants
        self.items: List[Any] = []
        self.children: Dict[str, GroupNode] = {}

        self.exemplar = None  # Item representing this node

        # Prevent circular import:
        # pylint: disable=import-outside-toplevel
        from .flat import FlatInserter
        from .tree import TreeInserter

        self._flat_inserter = FlatInserter(self)
        self._tree_inserter = TreeInserter(self)

    @property
    def item_count(self):
        return len(self.items)

    def insert_hierarchical(self, hashes: List[HashData], item):
        """ Interpret hashes as path in issue tree """
        self._tree_inserter.insert(hashes, item)
        self._update(item)

    def insert_flat(self, hashes: List[HashData], item):
        """ Interpret hashes as path in issue tree """
        self._flat_inserter.insert(hashes, item)
        self._update(item)

    def nodes(self, ancestors=None):
        """ Iterate nodes in a depth-first manner """
        if ancestors is None:
            ancestors = []
        yield self, ancestors

        for child in self.children.values():
            yield from child.nodes(ancestors + [self])

    def _update(self, item):
        """ Keep track of representative and item count """
        if self.exemplar is None:
            self.exemplar = item

        self.total_item_count += 1


class Inserter:

    """ Insertion strategy for a GroupNode """

    def __init__(self, node: GroupNode):

        self._node = node

    def _get_child(self, name: str, label: str) -> 'GroupNode':
        children = self._node.children
        if name not in children:
            child = children[name] = GroupNode(name, label)
        else:
            child = children[name]

        return child
