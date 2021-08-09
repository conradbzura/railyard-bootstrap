from __future__ import annotations

import importlib.metadata
import functools
import inspect
import sys
from typing import Any

from railyard.bootstrap.version._setup import _setup
from railyard.bootstrap.version._version import Version, VersionParser


__all__ = ["Version", "VersionParser"]


for plugin in importlib.metadata.entry_points()[
    "railyard.bootstrap.version.plugins"
]:
    plugin.load()


if "setuptools" in sys.modules:
    import setuptools

    frame = inspect.currentframe()
    module: Any = None
    while (
        frame
        and id(getattr(module, "setuptools", None)) != id(setuptools)
        and id(getattr(module, "setup", None)) != id(setuptools.setup)
    ):
        frame = frame.f_back
        module = inspect.getmodule(frame)
    if hasattr(module, "setuptools") or hasattr(module, "setuptools.setup"):
        module.setuptools.setup = functools.partial(
            _setup, module.setuptools.setup
        )
    elif hasattr(module, "setup"):
        module.setup = functools.partial(_setup, module.setup)
else:
    import setuptools

    setuptools.setup = functools.partial(_setup, setuptools.setup)
