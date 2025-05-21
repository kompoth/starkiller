"""Utilities to parse Python code."""

import ast
import itertools

import parso

from starkiller.models import (
    EditPosition,
    EditRange,
    ImportedName,
    ImportFromStatement,
    ImportModulesStatement,
    ModuleNames,
)
from starkiller.names_scanner import _NamesScanner


def parse_module(
    code: str,
    find_definitions: set[str] | None = None,
    *,
    check_internal_scopes: bool = False,
    collect_imported_attrs: bool = False,
) -> ModuleNames:
    """Parse Python source and find all definitions, undefined symbols usages and imported names.

    Args:
        code: Source code to be parsed.
        find_definitions: Optional set of definitions to look for.
        check_internal_scopes: If False, won't parse function and classes definitions.
        collect_imported_attrs: If True, will record attribute usages of ast.Name nodes.

    Returns:
        ModuleNames object.
    """
    visitor = _NamesScanner(find_definitions=find_definitions, collect_imported_attrs=collect_imported_attrs)
    visitor.visit(ast.parse(code))
    if check_internal_scopes:
        visitor.visit_internal_scopes()
    return ModuleNames(
        undefined=visitor.undefined,
        defined=visitor.defined,
        import_map=visitor.import_map,
        attr_usages=visitor.attr_usages,
    )


def find_imports(source: str, line_no: int) -> ImportModulesStatement | ImportFromStatement | None:
    """Checks if given line of python code contains from import statement.

    Args:
        source: Source code to check.
        line_no: Line number containing possible import statement.

    Returns:
        Module name and ImportedName list or `(None, None)`.
    """
    root = parso.parse(source)
    node = root.get_leaf_for_position((line_no, 1), include_prefixes=True)

    while node is not None and node.type not in {"import_from", "import_name"}:
        node = node.parent

    if node is None:
        return None

    edit_range = EditRange(EditPosition(*node.start_pos), EditPosition(*node.end_pos))

    if isinstance(node, parso.python.tree.ImportFrom):
        module_path = [n.value for n in node.get_from_names()]
        module = ".".join(module_path)
        if node.is_star_import():
            return ImportFromStatement(module, edit_range, is_star=True)

        imported_names = itertools.starmap(
            lambda n, a: ImportedName(n.value, None if not a else a.value),
            node._as_name_tuples(),  # noqa: SLF001
        )
        return ImportFromStatement(module, edit_range, names=set(imported_names))

    if isinstance(node, parso.python.tree.ImportName):
        imported_modules: list[ImportedName] = []
        for path, alias in node._dotted_as_names():  # noqa: SLF001
            module = ".".join(p.value for p in path)
            imported_modules.append(ImportedName(module, None if not alias else alias.value))
        return ImportModulesStatement(set(imported_modules), edit_range)

    return None
