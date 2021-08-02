import importlib.metadata

from railyard.bootstrap.version._version import Version, VersionParser  # noqa: F401

for plugin in importlib.metadata.entry_points()["railyard.bootstrap.version.plugins"]:
    plugin.load()
