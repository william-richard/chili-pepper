try:
    from typing import List
except ImportError:
    # python2.7 doesn't have typing, and I don't want to mess with mypy yet
    pass


class Kale:
    def __init__(self, app_name, bucket_name, runtime):
        # type: (str, str, str) -> None
        self._app_name = app_name
        self._bucket_name = bucket_name
        self._runtime = runtime
        self._function_handles = []

    @property
    def app_name(self):
        # type: () -> str
        return self._app_name

    @property
    def bucket_name(self):
        # type: () -> str
        return self._bucket_name

    @property
    def runtime(self):
        # type: () -> str
        return self._runtime

    @property
    def function_handles(self):
        # type: () -> List[str]
        return self._function_handles
