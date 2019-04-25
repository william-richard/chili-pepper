from collections.abc import MutableMapping


class Config(MutableMapping):
    def __init__(self):
        self._config = dict()
        self._config["aws"] = dict()

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
