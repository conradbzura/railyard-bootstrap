from __future__ import annotations

import enum
import functools
import re
from typing import (
    Callable,
    Generic,
    Optional,
    overload,
    Protocol,
    TypeVar,
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


T_get = TypeVar("T_get", bound=Sortable, covariant=True)
T_set = TypeVar("T_set", covariant=True)


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


class VersionSegment(int):
    def __new__(cls, value: Optional[Union[int, str]], format: str):
        if value is None:
            value = -1
        value = max(int(value), -1)
        return super().__new__(cls, value)

    def __init__(self, value: Optional[Union[int, str]], format: str):
        if value is None:
            value = -1
        value = max(int(value), -1)
        self.__VersionSegment_value__: int = value
        self.__VersionSegment_format__: str = format

    def __str__(self) -> str:
        return (
            self.__VersionSegment_format__.format(str(self.__VersionSegment_value__))
            if self.__VersionSegment_value__ > -1
            else ""
        )


class VersionSegmentDescriptor(Generic[T_get, T_set]):
    def __init__(
        self,
        factory: VersionSegmentFactory[T_get, T_set],
        default: Optional[Callable[[], T_get]] = None,
    ):
        self._factory: VersionSegmentFactory[T_get, T_set] = factory
        self._default: Callable[[], T_get] = default or (lambda: factory(None))

    def __get__(self, instance: Version, _) -> T_get:
        value = getattr(instance, self.private_name, None)
        if not value:
            value = self.default
            setattr(instance, self.private_name, value)
        return value

    def __set__(self, instance: Version, value: Optional[Union[T_get, T_set]]):
        segment = self._factory(value)
        default = self.default
        if segment < default:
            segment = default
        initial = getattr(instance, self.name)
        if segment > initial:
            setattr(instance, self.private_name, segment)
            for child in self.children:
                setattr(instance, child.private_name, child.default)
        elif segment < initial:
            raise ValueError("Version segments cannot be decremented!")

    def __set_name__(self, instance, name):
        self._name = name

    @property
    def children(self):
        segment_descriptors = [
            s for s in Version.__dict__.values() if isinstance(s, VersionSegmentDescriptor)
        ]
        yield from segment_descriptors[segment_descriptors.index(self) + 1 :]

    @property
    def default(self) -> T_get:
        return self._default()

    @property
    def name(self) -> str:
        return self._name

    @property
    def private_name(self) -> str:
        return f"_{self.name}"


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

    def __str__(self) -> str:
        return self.__ReleaseCycle_str__ or str(self)

    def __int__(self) -> int:
        return self.__ReleaseCycle_int__ or 0

    @classmethod
    def _missing_(cls, key: Union[int, str]) -> Optional[ReleaseCycle]:
        return cls.__ReleaseCycle_mapping__.get(key)


VersionSegmentFactory = Callable[[Optional[Union[T_get, T_set]]], T_get]


@functools.total_ordering
class Version:

    epoch = VersionSegmentDescriptor[VersionSegment, Union[int, str]](
        factory=lambda x: VersionSegment(x, format="{}!")
    )
    major_release = VersionSegmentDescriptor[VersionSegment, Union[int, str]](
        factory=lambda x: VersionSegment(x, format="{}"),
        default=lambda: VersionSegment(0, format="{}"),
    )
    minor_release = VersionSegmentDescriptor[VersionSegment, Union[int, str]](
        factory=lambda x: VersionSegment(x, format=".{}"),
        default=lambda: VersionSegment(0, format=".{}"),
    )
    release_cycle = VersionSegmentDescriptor[ReleaseCycle, Union[int, str, ReleaseCycle]](
        factory=lambda x: ReleaseCycle(x),
        default=lambda: ReleaseCycle.Alpha,
    )
    patch_release = VersionSegmentDescriptor[VersionSegment, Union[int, str]](
        factory=lambda x: VersionSegment(x, format="{}"),
        default=lambda: VersionSegment(0, format="{}"),
    )
    post_release = VersionSegmentDescriptor[VersionSegment, Union[int, str]](
        factory=lambda x: VersionSegment(x, format=".post{}")
    )
    dev_release = VersionSegmentDescriptor[VersionSegment, Union[int, str]](
        factory=lambda x: VersionSegment(x, format=".dev{}")
    )
    local_identifier = VersionSegmentDescriptor[str, str](factory=lambda x: x or "")

    def __init__(
        self,
        epoch: Optional[Union[int, str]] = None,
        major_release: Optional[Union[int, str]] = None,
        minor_release: Optional[Union[int, str]] = None,
        release_cycle: Optional[Union[int, str, ReleaseCycle]] = None,
        patch_release: Optional[Union[int, str]] = None,
        post_release: Optional[Union[int, str]] = None,
        dev_release: Optional[Union[int, str]] = None,
        local_identifier: Optional[str] = None,
    ):
        self.epoch = epoch
        self.major_release = major_release
        self.minor_release = minor_release
        self.release_cycle = release_cycle
        self.patch_release = patch_release
        self.post_release = post_release
        self.dev_release = dev_release
        self.local_identifier = local_identifier

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

    def __lt__(self, other: Version):
        for this, that in zip(self.segments, other.segments):
            if this < that:
                return True
            elif this > that:
                return False
        return (self.local_identifier or "") < (other.local_identifier or "")

    def __repr__(self) -> str:
        return (
            f"{type(self).__module__}"
            f".{type(self).__qualname__}"
            f"({repr(str(self))})"
        )

    def __str__(self) -> str:
        return self.full

    @staticmethod
    def parse(version: str, pattern: re.Pattern = DEFAULT_VERSION_PATTERN) -> Version:
        if pattern is not DEFAULT_VERSION_PATTERN:
            missing_capture_groups = set(DEFAULT_VERSION_PATTERN.groupindex.keys()) - set(
                pattern.groupindex.keys()
            )
            if missing_capture_groups:
                raise NonConformingVersionPattern(missing_capture_groups)
        match = pattern.match(version)
        if not match:
            raise NonConformingVersionString(version, pattern)
        segments: dict[str, Optional[str]] = match.groupdict()
        return Version(**segments)

    @property
    def public(self) -> str:
        return "".join(str(s) for s in self.segments)

    @property
    def local(self) -> str:
        return f"+{self.local_identifier}" if self.local_identifier is not None else ""

    @property
    def full(self) -> str:
        return self.public + self.local

    @property
    def segments(self):
        yield from (
            s for s in self.__dict__.values() if isinstance(s, (VersionSegment, ReleaseCycle))
        )
