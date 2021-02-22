from typing import Any, Dict, List


class GroupNode:

    """ Group of events. Subclasses differ in the way they insert / merge events """

    def __init__(self, name: str, item_processor):

        self.name = name

        self.total_item_count = 0  # Sum of items in self + descendants
        self.items: List[Any] = []
        self.children: Dict[str, GroupNode] = {}

        self.exemplar = None  # Item representing this node

        # Because items are passed down the tree,
        # make sure that each item processor is called only once
        if isinstance(item_processor, CachedItemProcessor):
            self._item_processor = item_processor
        else:
            print("Creating CIP for %s" % name)
            self._item_processor = CachedItemProcessor(item_processor)

    @property
    def item_count(self):
        return len(self.items)

    def insert(self, flat_hashes: List[str], hierarchical_hashes: List[str], item):
        is_exemplar = self.exemplar is None
        processed_item = self._item_processor(item, is_exemplar)

        self._insert(flat_hashes, hierarchical_hashes, item)

        if is_exemplar:
            self.exemplar = processed_item

        self.total_item_count += 1

    def visit(self, visitor, ancestors=None):
        if ancestors is None:
            ancestors = []
        visitor(self, ancestors)
        for child in self.children.values():
            child.visit(visitor, ancestors + [self])

    def _insert(self, flat_hashes: List[str], hierarchical_hashes: List[str], item):
        """ Override in subclasses """
        raise NotImplementedError

    @staticmethod
    def _child_type():
        """ Override in subclasses """
        raise NotImplementedError

    def _child(self, name):
        if name not in self.children:
            klass = self._child_type()
            child = self.children[name] = klass(name, self._item_processor)
        else:
            child = self.children[name]

        return child


class CachedItemProcessor:

    def __init__(self, item_processor):
        self._core_func = item_processor
        self._cache = {}

    def __call__(self, item, is_exemplar):
        cache_key = (id(item), is_exemplar)
        if cache_key in self._cache:
            result = self._cache[cache_key]
        else:
            result = self._cache[cache_key] = self._core_func(item, is_exemplar)

        return result