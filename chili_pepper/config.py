try:
    from collections.abc import MutableMapping
except ImportError:
    from collections import MutableMapping


class Config(MutableMapping):
    """Chili-Pepper specific configuration
    """

    def __init__(self):
        self._config = dict()
        self._config["aws"] = dict()
        self._config["default_environment_variables"] = dict()

    def __getitem__(self, key):
        return self._config.__getitem__(key)

    def __setitem__(self, key, value):
        return self._config.__setitem__(key, value)

    def __delitem__(self, key):
        return self._config.__delitem__(key)

    def __iter__(self):
        return self._config.__iter__()

    def __len__(self):
        return self._config.__len__()

    def __repr__(self):
        return repr(self._config)
