from __future__ import annotations

import sys

from ._version import Version


def _setup(setup, cmdclass=None, version=None, **kwargs):
    if not version:
        version = Version.parse.git()
    setup(cmdclass=cmdclass, version=str(version), **kwargs)
    del sys.modules["setuptools"]
