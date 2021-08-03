from __future__ import annotations

import enum
import functools
import re
import sys
from typing import (
    Callable,
    Optional,
    overload,
    Protocol,
    Union,
)


DEFAULT_VERSION_PATTERN: re.Pattern = re.compile(
    r"v?"
    r"((?P<epoch>\d+)(?:!))?"
    r"(?P<major_release>\d+)?"
    r"(?:(?:\.)(?P<minor_release>\d+))?"
    r"((?P<release_cycle>\.|a|b|rc)"
    r"(?P<patch_release>\d+))?"
    r"((?:\.post)(?P<post_release>\d+))?"
    r"((?:\.dev)(?P<dev_release>\d+))?"
    r"((?:\+)(?P<local_identifier>[a-zA-Z0-9.]+))?"
    r"$"
)


class Sortable(Protocol):
    def __lt__(self, other) -> bool:
        ...


def grammatical_series(*words: str) -> str:
    if len(words) > 2:
        separator = "; " if any("," in w for w in words) else ", "
        last = f"and {words[-1]}"
        return separator.join([*words[:-1], last])
    elif len(words) > 1:
        return " and ".join(words)
    elif words:
        return words[0]
    else:
        return ""


class NonConformingVersionString(Exception):
    def __init__(self, version: Optional[str], pattern: re.Pattern):
        super().__init__(
            f"Version string must match the specified pattern! Cannot parse "
            f"{repr(version)} with pattern r{repr(pattern.pattern)}."
        )


class NonConformingVersionPattern(Exception):
    def __init__(self, missing_capture_groups: set[str]):
        super().__init__(
            f"Version pattern must define all required capture groups! "
            f"Missing capture groups "
            f"{grammatical_series(*sorted(missing_capture_groups))}."
        )


class IntVersionSegment(int):
    def __new__(cls, value: Optional[Union[int, str]], format: str):
        if value is None:
            value = -1
        value = max(int(value), -1)
        return super().__new__(cls, value)

    def __init__(self, value: Optional[Union[int, str]], format: str):
        if value is None:
            value = -1
        value = max(int(value), -1)
        self.__IntVersionSegment_value__: int = value
        self.__IntVersionSegment_format__: str = format

    def __repr__(self) -> str:
        return (
            f"<{type(self).__qualname__}: "
            f"{repr(self.__IntVersionSegment_value__)}>"
        )

    def render(self) -> str:
        return (
            self.__IntVersionSegment_format__.format(
                str(self.__IntVersionSegment_value__)
            )
            if self.__IntVersionSegment_value__ > -1
            else ""
        )


class StrVersionSegment(str):
    def __new__(cls, value: Optional[str], format: str):
        if value is None:
            value = ""
        return super().__new__(cls, value)

    def __init__(self, value: Optional[str], format: str):
        if value is None:
            value = ""
        self.__StrVersionSegment_value__: str = value
        self.__StrVersionSegment_format__: str = format

    def __repr__(self) -> str:
        return (
            f"<{type(self).__qualname__}: "
            f"{repr(self.__StrVersionSegment_value__)}>"
        )

    def render(self) -> str:
        return (
            self.__StrVersionSegment_format__.format(
                str(self.__StrVersionSegment_value__)
            )
            if self.__StrVersionSegment_value__
            else ""
        )


@functools.total_ordering
class ReleaseCycle(metaclass=enum.EnumMeta):

    __ReleaseCycle_mapping__: dict[Union[int, str], ReleaseCycle] = {}
    __ReleaseCycle_int__: Optional[int] = None
    __ReleaseCycle_str__: Optional[str] = None

    Alpha = 0, "a"
    Beta = 1, "b"
    ReleaseCandidate = 2, "rc"
    Production = 3, "."

    @overload
    def __new__(cls, integer: int, string: str):
        ...

    @overload
    def __new__(cls, key: Optional[Union[int, str, ReleaseCycle]]):
        ...

    def __new__(cls, integer, string):
        self = object.__new__(cls)
        self.__ReleaseCycle_int__ = integer
        self.__ReleaseCycle_str__ = string
        cls.__ReleaseCycle_mapping__.update({integer: self, string: self})
        return self

    def __lt__(self, other: ReleaseCycle) -> bool:
        return int(self).__lt__(int(ReleaseCycle(other)))

    def __int__(self) -> int:
        return self.__ReleaseCycle_int__ or 0

    @classmethod
    def _missing_(cls, key: Union[int, str]) -> Optional[ReleaseCycle]:
        return cls.__ReleaseCycle_mapping__.get(key)

    def render(self) -> str:
        return self.__ReleaseCycle_str__ or str(self)


class VersionParser:
    def __call__(
        self, version: str, pattern: re.Pattern = DEFAULT_VERSION_PATTERN
    ) -> Version:
        if __name__ in sys.modules:
            del sys.modules[__name__]
        if pattern is not DEFAULT_VERSION_PATTERN:
            missing_capture_groups = set(
                DEFAULT_VERSION_PATTERN.groupindex.keys()
            ) - set(pattern.groupindex.keys())
            if missing_capture_groups:
                raise NonConformingVersionPattern(missing_capture_groups)
        match = pattern.match(version)
        if not match:
            raise NonConformingVersionString(version, pattern)
        segments: dict[str, str] = {
            k: v for k, v in match.groupdict().items() if v is not None
        }
        return Version(**segments)

    @classmethod
    def plugin(cls, alias: str):
        def decorator(decorated: Callable[[], str]) -> Callable[[], str]:
            setattr(
                cls,
                alias,
                functools.wraps(decorated)(lambda self: self(decorated())),
            )
            return decorated

        return decorator


VersionSegment = Optional[
    Union[IntVersionSegment, StrVersionSegment, ReleaseCycle]
]


@functools.total_ordering
class Version:

    parse = VersionParser()

    segment = type("segment", (property,), {})

    def __init__(
        self,
        epoch: Optional[Union[int, str]] = None,
        major_release: Union[int, str] = 0,
        minor_release: Optional[Union[int, str]] = None,
        release_cycle: Optional[Union[int, str, ReleaseCycle]] = None,
        patch_release: Optional[Union[int, str]] = None,
        post_release: Optional[Union[int, str]] = None,
        dev_release: Optional[Union[int, str]] = None,
        local_identifier: Optional[str] = None,
    ):
        assert major_release is not None, "Major release cannot be undefined!"
        assert (release_cycle is None) == (
            patch_release is None
        ), "Patch release and release cycle must be defined together!"
        if patch_release is not None:
            assert (
                minor_release is not None
            ), "Minor release cannot be undefined if patch release is defined!"
        self._epoch = epoch
        self._major_release = major_release
        self._minor_release = minor_release
        self._release_cycle = release_cycle
        self._patch_release = patch_release
        self._post_release = post_release
        self._dev_release = dev_release
        self._local_identifier = local_identifier

        self._dict = {
            k: getattr(self, k)
            for k, v in type(self).__dict__.items()
            if isinstance(v, self.segment)
        }

    def __eq__(self, other: object):
        if not isinstance(other, Version):
            return super().__eq__(other)
        else:
            return all(
                (
                    self.epoch == other.epoch,
                    self.major_release == other.major_release,
                    self.minor_release == other.minor_release,
                    self.release_cycle == other.release_cycle,
                    self.patch_release == other.patch_release,
                    self.post_release == other.post_release,
                    self.dev_release == other.dev_release,
                    self.local_identifier == other.local_identifier,
                )
            )

    @overload
    def __getitem__(self, item: slice) -> dict[str, VersionSegment]:
        ...

    @overload
    def __getitem__(self, item: str) -> VersionSegment:
        ...

    def __getitem__(self, item):
        if isinstance(item, slice):
            segments = self.segments
            if item.start:
                start = segments.index(item.start)
            else:
                start = None
            if item.stop:
                stop = segments.index(item.stop)
                if stop > len(segments):
                    stop = None
            else:
                stop = None
            return {k: v for k, v in list(self.items())[slice(start, stop)]}
        else:
            return self._dict[item]

    def __iter__(self):
        return iter(self._dict)

    def __lt__(self, other: Version) -> bool:
        for this, that in zip(self.segments, other.segments):
            if this is None:
                this = -1
            if that is None:
                that = -1
            if this < that:
                return True
            elif this > that:
                return False
        return False

    def __repr__(self) -> str:
        return f"<{type(self).__qualname__}: {repr(str(self))}>"

    def __str__(self) -> str:
        return "".join(v.render() for v in self.values() if v is not None)

    @segment
    def epoch(self) -> Optional[IntVersionSegment]:
        return (
            self._epoch
            if self._epoch is None
            else IntVersionSegment(self._epoch, format="{}!")
        )

    @segment
    def major_release(self) -> Optional[IntVersionSegment]:
        return IntVersionSegment(self._major_release, format="{}")

    @segment
    def minor_release(self) -> Optional[IntVersionSegment]:
        return IntVersionSegment(self._minor_release, format=".{}")

    @segment
    def release_cycle(self) -> Optional[ReleaseCycle]:
        return ReleaseCycle(self._release_cycle)

    @segment
    def patch_release(self) -> Optional[IntVersionSegment]:
        return IntVersionSegment(self._patch_release, format="{}")

    @segment
    def post_release(self) -> Optional[IntVersionSegment]:
        return (
            self._post_release
            if self._post_release is None
            else IntVersionSegment(self._post_release, format=".post{}")
        )

    @segment
    def dev_release(self) -> Optional[IntVersionSegment]:
        return (
            self._dev_release
            if self._dev_release is None
            else IntVersionSegment(self._dev_release, format=".dev{}")
        )

    @segment
    def local_identifier(self) -> Optional[StrVersionSegment]:
        return (
            self._local_identifier
            if self._local_identifier is None
            else StrVersionSegment(self._local_identifier, format="+{}")
        )

    @property
    def local(self) -> str:
        return "".join(
            v.render()
            for v in self[type(self).local_identifier :].values()
            if v is not None
        )

    @property
    def public(self) -> str:
        return "".join(
            v.render()
            for v in self[: type(self).local_identifier].values()
            if v is not None
        )

    @property
    def segments(self):
        return [
            v
            for v in type(self).__dict__.values()
            if isinstance(v, self.segment)
        ]

    def keys(self):
        return self._dict.keys()

    def items(self):
        return self._dict.items()

    def values(self):
        return self._dict.values()
