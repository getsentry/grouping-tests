from typing import Dict, List
import logging

from .base import GroupNode


LOG = logging.getLogger(__name__)


class ListNode(GroupNode):

    """ Represents a flat list of event groups """

    def __init__(self, *args, **kwargs):

        super(ListNode, self).__init__(*args, **kwargs)

        #: Lookup groups by hash. Values can occur multiple times
        self._lookup = {}

    def _insert(self, flat_hashes: List[str], hierarchical_hashes: List[str], item):
        """ Events with overlapping hashes are grouped together """
        candidates = self._candidates(flat_hashes)
        if candidates:
            # Add event to exising group
            group, *tail = candidates
            if tail:
                LOG.warn("Multiple group candidates for item %s", item)
        else:
            # Add event to a new group
            group = self._child(",".join(flat_hashes))  # TODO: use better name for child
            for hash_ in flat_hashes:
                self._lookup[hash_] = group

        group.insert([], [], item)

    def _candidates(self, flat_hashes: List[str]):
        # Use a dict to prevent duplicates
        candidates = {
            id(self._lookup[hash_]): self._lookup[hash_]
            for hash_ in flat_hashes if hash_ in self._lookup
        }

        return candidates.values()

    @staticmethod
    def _child_type():
        return ListElementNode


class ListElementNode(GroupNode):

    """ Represents a group which is part of a flat list """

    def _insert(self, flat_hashes: List[str], hierarchical_hashes: List[str], item):
        """ Add the item without creating any additional hierarchy """
        self.items.append(item)