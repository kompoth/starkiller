import dataclasses
import logging
import pathlib

from lsprotocol.converters import get_converter  # type: ignore
from lsprotocol.types import (  # type: ignore
    CodeAction,
    CodeActionKind,
    Position,
    Range,
    TextEdit,
    WorkspaceEdit,
)
from pylsp import hookimpl  # type: ignore
from pylsp.config.config import Config  # type: ignore
from pylsp.workspace import Document, Workspace  # type: ignore

from starkiller.parsing import ImportedName, find_from_import, find_import, parse_module
from starkiller.project import StarkillerProject
from starkiller.refactoring import get_attrs_as_names_edits, get_rename_edits

log = logging.getLogger(__name__)
converter = get_converter()

DEFAULT_ALIASES = {
    "numpy": "np",
    "pandas": "pd",
    "matplotlib.pyplot": "plt",
    "seaborn": "sns",
    "tensorflow": "tf",
    "sklearn": "sk",
    "statsmodels": "sm",
}


@dataclasses.dataclass
class PluginSettings:
    enabled: bool = False
    aliases: dict[str, str] = dataclasses.field(default_factory=lambda: DEFAULT_ALIASES)


@hookimpl
def pylsp_settings() -> dict:
    return dataclasses.asdict(PluginSettings())


@hookimpl
def pylsp_code_actions(
    config: Config,
    workspace: Workspace,
    document: Document,
    range: dict,  # noqa: A002
    context: dict,  # noqa: ARG001
) -> list[dict]:
    code_actions: list[CodeAction] = []
    project_path = pathlib.Path(workspace.root_path).resolve()
    env_path = project_path / ".venv"
    project = StarkillerProject(
        project_path,
        env_path=env_path if env_path.exists() else None,
    )

    config = workspace._config  # noqa: SLF001
    plugin_settings = config.plugin_settings("starkiller", document_path=document.path)
    aliases = plugin_settings.get("aliases", [])

    active_range = converter.structure(range, Range)
    line = document.lines[active_range.start.line].rstrip("\r\n")
    line_range = Range(
        start=Position(line=active_range.start.line, character=0),
        end=Position(line=active_range.start.line, character=len(line)),
    )

    from_module, imported_names = find_from_import(line)
    imported_modules = find_import(line)

    if from_module and imported_names:
        if any(name.name == "*" for name in imported_names):
            code_actions.extend(get_ca_for_star_import(document, project, from_module, line_range, aliases))
        else:
            code_actions.extend(get_ca_for_from_import(document, from_module, imported_names, line_range, aliases))
    elif imported_modules:
        code_actions.extend(get_ca_for_module_import(document, imported_modules, line_range))

    return converter.unstructure(code_actions)


def get_ca_for_star_import(
    document: Document,
    project: StarkillerProject,
    from_module: str,
    import_line_range: Range,
    aliases: dict,
) -> list[CodeAction]:
    undefined_names = parse_module(document.source, check_internal_scopes=True).undefined
    if not undefined_names:
        return [get_ca_remove_unnecessary_import(document, import_line_range)]

    externaly_defined = project.find_definitions(from_module, set(undefined_names))
    if not externaly_defined:
        return [get_ca_remove_unnecessary_import(document, import_line_range)]

    text_edits_from = get_edits_replace_module_w_from(from_module, externaly_defined, import_line_range)
    text_edits_module = get_edits_replace_from_w_module(
        document.source,
        from_module,
        {ImportedName(name) for name in externaly_defined},
        import_line_range,
        aliases,
    )

    return [
        CodeAction(
            title="Starkiller: Replace * with explicit names",
            kind=CodeActionKind.SourceOrganizeImports,
            edit=WorkspaceEdit(changes={document.uri: text_edits_from}),
        ),
        CodeAction(
            title="Starkiller: Replace * import with module import",
            kind=CodeActionKind.SourceOrganizeImports,
            edit=WorkspaceEdit(changes={document.uri: text_edits_module}),
        ),
    ]


def get_ca_for_module_import(
    document: Document,
    imported_modules: list[ImportedName],
    line_range: Range,
) -> list[CodeAction]:
    parsed = parse_module(document.source, check_internal_scopes=True, collect_imported_attrs=True)

    if len(parsed.imported_attr_usages) > 1:
        return []

    imported_name = imported_modules[0]
    used_attrs = parsed.imported_attr_usages.get(imported_name.alias or imported_name.name)
    if not used_attrs:
        return [get_ca_remove_unnecessary_import(document, line_range)]

    text_edits = get_edits_replace_module_w_from(imported_name.name, used_attrs, line_range)

    for edit_range, new_value in get_attrs_as_names_edits(
        document.source, imported_name.alias or imported_name.name, used_attrs
    ):
        rename_range = Range(
            start=Position(line=edit_range.start.line, character=edit_range.start.char),
            end=Position(line=edit_range.end.line, character=edit_range.end.char),
        )
        text_edits.append(TextEdit(range=rename_range, new_text=new_value))

    return [
        CodeAction(
            title="Starkiller: Replace module import with from import",
            kind=CodeActionKind.SourceOrganizeImports,
            edit=WorkspaceEdit(changes={document.uri: text_edits}),
        )
    ]


def get_ca_for_from_import(
    document: Document,
    from_module: str,
    imported_names: set[ImportedName],
    import_line_range: Range,
    aliases: dict,
) -> list[CodeAction]:
    text_edits = get_edits_replace_from_w_module(
        document.source,
        from_module,
        imported_names,
        import_line_range,
        aliases,
    )
    return [
        CodeAction(
            title="Starkiller: Replace from import with module import",
            kind=CodeActionKind.SourceOrganizeImports,
            edit=WorkspaceEdit(changes={document.uri: text_edits}),
        )
    ]


def get_edits_replace_module_w_from(
    from_module: str,
    names: set[str],
    import_line_range: Range,
) -> list[TextEdit]:
    names_str = ", ".join(names)
    new_text = f"from {from_module} import {names_str}"
    return [TextEdit(range=import_line_range, new_text=new_text)]


def get_edits_replace_from_w_module(
    source: str,
    from_module: str,
    names: set[ImportedName],
    import_line_range: Range,
    aliases: dict[str, str],
) -> list[TextEdit]:
    new_text = f"import {from_module}"
    if from_module in aliases:
        alias = aliases[from_module]
        new_text += f" as {alias}"
    text_edits = [TextEdit(range=import_line_range, new_text=new_text)]

    rename_map = {n.alias or n.name: f"{from_module}.{n.name}" for n in names}
    for edit_range, new_value in get_rename_edits(source, rename_map):
        rename_range = Range(
            start=Position(line=edit_range.start.line, character=edit_range.start.char),
            end=Position(line=edit_range.end.line, character=edit_range.end.char),
        )
        text_edits.append(TextEdit(range=rename_range, new_text=new_value))
    return text_edits


def get_ca_remove_unnecessary_import(
    document: Document,
    import_line_range: Range,
) -> CodeAction:
    import_line_num = import_line_range.start.line
    import_line = document.lines[import_line_num]

    if import_line != len(document.lines) - 1:
        end = Position(line=import_line_num + 1, character=0)
    else:
        end = Position(line=import_line_num, character=len(import_line) - 1)

    replace_range = Range(start=Position(line=import_line_num, character=0), end=end)
    text_edit = TextEdit(range=replace_range, new_text="")

    workspace_edit = WorkspaceEdit(changes={document.uri: [text_edit]})
    return CodeAction(
        title="Starkiller: Remove unnecessary import",
        kind=CodeActionKind.SourceOrganizeImports,
        edit=workspace_edit,
    )
