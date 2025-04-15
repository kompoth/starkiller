# ruff: noqa: N802
"""Utilities to change Python code."""

from collections.abc import Generator
from dataclasses import dataclass

import parso


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


def get_rename_edits(source: str, rename_map: dict[str, str]) -> Generator[tuple[EditRange, str]]:
    """Generates source code changes to rename symbols. Doesn't affect imports.

    Args:
        source: Source code being refactored.
        rename_map: Rename mapping, old name VS new name.

    Yields:
        EditRange and edit text.
    """
    root = parso.parse(source)
    for old_name, nodes in root.get_used_names().items():
        if old_name in rename_map:
            for node in nodes:
                if node.search_ancestor("import_as_names", "import_from", "import_name"):
                    continue

                edit_range = EditRange(
                    start=EditPosition(
                        line=node.start_pos[0] - 1,
                        char=node.start_pos[1],
                    ),
                    end=EditPosition(
                        line=node.end_pos[0] - 1,
                        char=node.end_pos[1],
                    ),
                )
                yield (edit_range, rename_map[old_name])


def get_attrs_as_names_edits(source: str, name: str, attrs: set[str]):
    root = parso.parse(source)
    nodes = root.get_used_names().get(name, [])
    for node in nodes:
        operator_leaf = node.get_next_leaf()
        if not isinstance(operator_leaf, parso.python.tree.Operator) or operator_leaf.value != ".":
            continue
        attr_leaf = operator_leaf.get_next_leaf()
        if attr_leaf.value not in attrs:
            continue

        edit_range = EditRange(
            start=EditPosition(
                line=node.start_pos[0] - 1,
                char=node.start_pos[1],
            ),
            end=EditPosition(
                line=operator_leaf.end_pos[0] - 1,
                char=operator_leaf.end_pos[1],
            ),
        )

        yield (edit_range, "")
