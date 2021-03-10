from typing import List

from .base import HashData, Inserter

class TreeInserter(Inserter):

    def insert(self, hierarchical_hashes: List[HashData], item):
        """ Event hashes are interpreted as a path down a tree of event groups """
        if hierarchical_hashes:
            head, *tail = hierarchical_hashes
            self._get_child(head.hash, head.label).insert_hierarchical(tail, item)
        else:
            # We have reached our destination
            self._node.items.append(item)
