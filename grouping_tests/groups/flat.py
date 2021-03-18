from typing import List
import logging

from .base import HashData, Inserter


LOG = logging.getLogger(__name__)


class FlatInserter(Inserter):

    """ Represents a flat list of event groups """

    def __init__(self, *args, **kwargs):

        super(FlatInserter, self).__init__(*args, **kwargs)

        #: Lookup groups by hash. Values can occur multiple times
        self._lookup = {}

    def insert(self, flat_hashes: List[HashData], item):
        """ Events with overlapping hashes are grouped together """

        if not flat_hashes:
            # End of recursion
            self._node.items.append(item)
        else:
            candidates = self._candidates(flat_hashes)
            if candidates:
                # Add event to exising group
                group, *tail = candidates
                if tail:
                    LOG.warning("Multiple group candidates for item %s", item)
            else:
                # Add event to a new group
                name = "-".join(d.hash for d in flat_hashes)
                group = self._get_child(name, None)
                for d in flat_hashes:
                    self._lookup[d.hash] = group

            # Call the GroupNode for bookkeeping
            group.insert_flat([], item)

    def _candidates(self, flat_hashes: List[HashData]):
        # Use a dict to prevent duplicates
        candidates = {
            id(self._lookup[d.hash]): self._lookup[d.hash]
            for d in flat_hashes if d.hash in self._lookup
        }

        return candidates.values()
