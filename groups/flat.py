from typing import Dict, List

from .base import EventGroup


class FlatGroup(EventGroup):

    """ Represent a flat list of event groups """

    def insert(self, flat_hashes: List[str], hierarchical_hashes: List[str], item):
        """ Events with overlapping hashes are grouped together """
        raise NotImplementedError
