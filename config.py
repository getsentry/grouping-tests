from pathlib import Path
import json

from sentry.grouping import api as grouping_api


class Config:

    """ Contains all necessary grouping config """

    def __init__(self, config_path: Path):
        with open(config_path, 'r') as config_file:
            config = json.load(config_file)

        self._grouping_config = self._load_grouping_config(config)
        self._normalize_stacktraces = config['normalize_stacktraces']

    @property
    def grouping_config(self):
        return self._grouping_config

    @property
    def normalize_stacktraces(self):
        return self._normalize_stacktraces

    @staticmethod
    def _load_grouping_config(config):
        strategy_config = config['strategy_config']
        return grouping_api.load_grouping_config(strategy_config)