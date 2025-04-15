# ruff: noqa: N802
"""Utilities to parse Python code."""

import ast
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass

from starkiller.utils import BUILTIN_FUNCTIONS


@dataclass(frozen=True)
class ImportedName:
    """Imported name structure."""

    name: str
    alias: str | None = None


@dataclass(frozen=True)
class ModuleNames:
    """Names used in a module."""

    undefined: set[str]
    defined: set[str]
    import_map: dict[str, set[ImportedName]]
    imported_attr_usages: dict[str, set[str]]


@dataclass(frozen=True)
class _LocalScope:
    name: str
    body: list[ast.stmt]
    args: list[str] | None = None


class _ScopeVisitor(ast.NodeVisitor):
    def __init__(self, find_definitions: set[str] | None = None, *, collect_imported_attrs: bool = False) -> None:
        super().__init__()

        # Names that were used but never initialized in this module
        self._undefined: set[str] = set()

        # Names initialized in this module
        self._defined: set[str] = set()

        # Names imported from elsewhere
        self._import_map: dict[str, set[ImportedName]] = {}
        self._imported: set[str] = set()

        # Stop iteration on finding all of these names
        self._find_definitions = None if find_definitions is None else dict.fromkeys(find_definitions, False)

        # Internal scopes must be checked after visiting the top level
        self._internal_scopes: list[_LocalScope] = []

        # How to treat ast.Name: if True, this might be a definition
        self._in_definition_context = False

        # If True, will record attribute usages of ast.Name nodes
        self._collect_imported_attrs = collect_imported_attrs
        self._attr_usages: dict[str, set[str]] = {}

    def visit(self, node: ast.AST) -> None:
        if self._find_definitions and all(self._find_definitions.values()):
            return
        super().visit(node)

    def visit_internal_scopes(self) -> None:
        for scope in self._internal_scopes:
            scope_visitor = _ScopeVisitor(find_definitions=None, collect_imported_attrs=self._collect_imported_attrs)

            # Known names
            scope_visitor._defined = self._defined.copy()
            if scope.args:
                scope_visitor._defined.update(scope.args)
            scope_visitor._import_map = self._import_map.copy()
            scope_visitor._imported = self._imported.copy()

            # Visit scope body and all internal scopes
            for scope_node in scope.body:
                scope_visitor.visit(scope_node)
            scope_visitor.visit_internal_scopes()

            # Update upper scope undefined names set
            self._undefined.update(scope_visitor.undefined)
            self._attr_usages.update(scope_visitor.imported_attr_usages)

    @property
    def defined(self) -> set[str]:
        # If we were looking for specific names, return only names from that list
        if self._find_definitions is not None:
            found_names = {name for name, found in self._find_definitions.items() if found}
            return found_names & self._defined
        return self._defined.copy()

    @property
    def undefined(self) -> set[str]:
        return self._undefined.copy()

    @property
    def import_map(self) -> dict[str, set[ImportedName]]:
        return self._import_map.copy()

    @property
    def imported_attr_usages(self) -> dict[str, set[str]]:
        return {module: attrs for module, attrs in self._attr_usages.items() if module in self._imported}

    @contextmanager
    def definition_context(self) -> Generator[None]:
        # This is not thread safe! Consider using thead local data to store definition context state.
        # Context manager is used in this class to control new names treatment: either to record them as definitions or
        # as possible usages of undefined names.
        self._in_definition_context = True
        yield
        self._in_definition_context = False

    def record_import_from_module(self, module_name: str, name: str, alias: str | None = None) -> None:
        imported_name = ImportedName(name, alias)
        self._import_map.setdefault(module_name, set())
        self._import_map[module_name].add(imported_name)
        self._imported.add(alias or name)

    def _record_definition(self, name: str) -> None:
        # Make sure the name wasn't used with no initialization
        if name not in (self._undefined | self._imported):
            self._defined.add(name)

            # If searching for definitions, cross out already found
            if self._find_definitions is not None and name in self._find_definitions:
                self._find_definitions[name] = True

    def _record_undefined_name(self, name: str) -> None:
        # Record only uninitialised uses
        if name not in (self._defined | self._imported | BUILTIN_FUNCTIONS):
            self._undefined.add(name)

    def record_name(self, name: str) -> None:
        if self._in_definition_context:
            self._record_definition(name)
        else:
            self._record_undefined_name(name)

    def visit_Name(self, node: ast.Name) -> None:
        self.record_name(node.id)

    def visit_Import(self, node: ast.Import) -> None:
        for name in node.names:
            self.record_import_from_module(
                module_name=name.name,
                name=name.name,
                alias=name.asname,
            )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module_name = "." * node.level
        if node.module:
            module_name += node.module

        for name in node.names:
            self.record_import_from_module(
                module_name=module_name,
                name=name.name,
                alias=name.asname,
            )

    def visit_Assign(self, node: ast.Assign) -> None:
        with self.definition_context():
            for target in node.targets:
                self.visit(target)
        self.visit(node.value)

    def visit_Call(self, node: ast.Call) -> None:
        # Called a function, not an attribute method
        if isinstance(node.func, ast.Name | ast.Attribute):
            self.visit(node.func)

        # Values passed as arguments
        for arg in node.args:
            self.visit(arg)
        for kwarg in node.keywords:
            self.visit(kwarg.value)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        owner = node.value
        if isinstance(owner, ast.Attribute | ast.Call | ast.Name):
            self.visit(owner)

        if isinstance(owner, ast.Name) and self._collect_imported_attrs:
            self._attr_usages.setdefault(owner.id, set()).add(node.attr)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._record_definition(node.name)

        for decorator in node.decorator_list:
            self.visit(decorator)
        for base in node.bases:
            self.visit(base)
        for kwarg in node.keywords:
            self.visit(kwarg.value)
        # TODO: type_params

        self._internal_scopes.append(
            _LocalScope(
                name=node.name,
                body=node.body.copy(),
                args=[],
            ),
        )

    def _visit_callable(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        with self.definition_context():
            self.record_name(node.name)

        args = node.args.posonlyargs + node.args.args + node.args.kwonlyargs

        # Check for no inits
        for decorator in node.decorator_list:
            self.visit(decorator)
        for arg in args:
            if arg.annotation:
                self.visit(arg.annotation)
        for default in node.args.defaults + node.args.kw_defaults:
            if default is not None:
                self.visit(default)
        if node.returns:
            self.visit(node.returns)

        self._internal_scopes.append(
            _LocalScope(
                name=node.name,
                body=node.body.copy(),
                args=[arg.arg for arg in args],
            ),
        )

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_callable(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_callable(node)


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
    visitor = _ScopeVisitor(find_definitions=find_definitions, collect_imported_attrs=collect_imported_attrs)
    visitor.visit(ast.parse(code))
    if check_internal_scopes:
        visitor.visit_internal_scopes()
    return ModuleNames(
        undefined=visitor.undefined,
        defined=visitor.defined,
        import_map=visitor.import_map,
        imported_attr_usages=visitor.imported_attr_usages,
    )


def find_from_import(line: str) -> tuple[str, set[ImportedName]] | tuple[None, None]:
    """Checks if given line of python code contains from import statement.

    Args:
        line: Line of code to check.

    Returns:
        Module name and ImportedName list or `(None, None)`.
    """
    body = ast.parse(line).body
    if len(body) == 0 or not isinstance(body[0], ast.ImportFrom):
        return None, None

    node = body[0]
    module_name = "." * node.level
    if node.module:
        module_name += node.module
    imported_names = {ImportedName(name=name.name, alias=name.asname) for name in node.names}
    return module_name, imported_names


def find_import(line: str) -> list[ImportedName] | None:
    """Checks if given line of python code contains import statement.

    Args:
        line: Line of code to check.

    Returns:
        ImportedName or None.
    """
    body = ast.parse(line).body
    if len(body) == 0 or not isinstance(body[0], ast.Import):
        return None

    node = body[0]
    return [ImportedName(name=name.name, alias=name.asname) for name in node.names]
