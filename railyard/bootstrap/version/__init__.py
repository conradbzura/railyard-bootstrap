from __future__ import annotations

import importlib.metadata

from railyard.bootstrap.version._version import Version


__all__ = ["Version"]


for plugin in importlib.metadata.entry_points()[
    "railyard.bootstrap.version.plugins"
]:
    plugin.load()
