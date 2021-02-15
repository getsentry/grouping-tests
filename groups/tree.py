from typing import List

from .base import EventGroup

class TreeGroup(EventGroup):

    """ Represent a tree of event groups """

    def insert(self, hashes: List[str], item):
        """ Event hashes are interpreted as a path down a tree of event groups """
        if hashes:
            head, *tail = hashes
            self._child(head).insert(tail, item)
        else:
            self.items.append(item)
        self.item_count += 1