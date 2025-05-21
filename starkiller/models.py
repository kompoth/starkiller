"""Data structures."""

from ast import stmt
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ImportedName:
    """Imported name structure."""

    name: str
    alias: str | None = None


@dataclass(frozen=True)
class ModuleNames:
    """Names and attributes used in a module."""

    undefined: set[str]
    defined: set[str]
    import_map: dict[str, set[ImportedName]]
    attr_usages: dict[str, set[str]]


@dataclass
class EditPosition:
    """Coordinate in source."""

    line: int
    char: int


@dataclass
class EditRange:
    """Coordinates of source change."""

    start: EditPosition
    end: EditPosition


@dataclass(frozen=True)
class ImportFromStatement:
    """`from <module> import <names>` statement."""

    module: str
    import_range: EditRange
    is_star: bool = False
    names: set[ImportedName] | None = None


@dataclass(frozen=True)
class ImportModulesStatement:
    """`import <module>` statement."""

    modules: set[ImportedName]
    import_range: EditRange


@dataclass
class Module:
    """Universal module type."""
    name: str
    fullname: str
    path: Path
    submodule_paths: list[Path] | None = None

    @property
    def package(self) -> bool:
        """Whether is module is a package."""
        return bool(self.submodule_paths)


@dataclass(frozen=True)
class _LocalScope:
    name: str
    body: list[stmt]
    args: list[str] | None = None
