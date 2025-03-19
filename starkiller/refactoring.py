# ruff: noqa: N802
"""Utilities to change Python code."""

from collections.abc import Generator
from dataclasses import dataclass

import parso


@dataclass
class _EditPosition:
    line: int
    char: int


@dataclass
class _EditRange:
    start: _EditPosition
    end: _EditPosition


def _get_rename_edits(code: str, rename_map: dict[str, str]) -> Generator[tuple[_EditRange, str]]:
    root = parso.parse(code)
    for old_name, nodes in root.get_used_names().items():
        if old_name in rename_map:
            for node in nodes:
                edit_range = _EditRange(
                    start=_EditPosition(
                        line=node.start_pos[0] - 1,
                        char=node.start_pos[1],
                    ),
                    end=_EditPosition(
                        line=node.end_pos[0] - 1,
                        char=node.end_pos[1],
                    ),
                )
                yield (edit_range, rename_map[old_name])
