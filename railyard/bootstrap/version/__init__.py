import importlib.metadata

from railyard.bootstrap.version._version import (  # noqa: F401
    Version,
    VersionParser,
)

for plugin in importlib.metadata.entry_points()[
    "railyard.bootstrap.version.plugins"
]:
    plugin.load()
