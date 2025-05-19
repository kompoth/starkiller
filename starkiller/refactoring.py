"""Utilities to change Python code."""

from collections.abc import Generator

import parso

from starkiller.models import EditPosition, EditRange


def rename(source: str, rename_map: dict[str, str]) -> Generator[tuple[EditRange, str]]:
    """Generate rename edits.

    Generates source code changes to rename names from rename_map. Doesn't affect imports.

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
                # Ignore imports
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


def strip_base_name(source: str, base_name: str, attrs: set[str]) -> Generator[tuple[EditRange, str]]:
    """Generate base name strip edits for attribute calls.

    Finds all base_name usages with attributes and generates edits stripping the base_name. Doesn't affect imports.

    Args:
        source: Source code being refactored.
        base_name: Target name.
        attrs: Attributes to be converted.

    Yields:
        EditRange and edit text.
    """
    root = parso.parse(source)
    nodes = root.get_used_names().get(base_name, [])
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
