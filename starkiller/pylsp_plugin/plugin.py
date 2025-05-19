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

from starkiller.parsing import ImportedName, ImportFromStatement, ImportModulesStatement, find_imports, parse_module
from starkiller.project import StarkillerProject
from starkiller.refactoring import rename, strip_base_name

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
    line_no = active_range.start.line + 1

    import_statement = find_imports(document.source, line_no)
    if import_statement is None:
        return []
    import_range = Range(
        start=Position(
            line=import_statement.import_range.start.line - 1,
            character=import_statement.import_range.start.char,
        ),
        end=Position(
            line=import_statement.import_range.end.line - 1,
            character=import_statement.import_range.end.char,
        ),
    )

    if isinstance(import_statement, ImportFromStatement):
        if import_statement.is_star:
            code_actions.extend(
                get_ca_for_star_import(document, project, import_statement.module, import_range, aliases)
            )
        else:
            imported_names = import_statement.names or set()
            code_actions.extend(
                get_ca_for_from_import(document, import_statement.module, imported_names, import_range, aliases)
            )
    elif isinstance(import_statement, ImportModulesStatement):
        code_actions.extend(get_ca_for_module_import(document, import_statement.modules, import_range))

    return converter.unstructure(code_actions)


def get_ca_for_star_import(
    document: Document,
    project: StarkillerProject,
    from_module: str,
    import_range: Range,
    aliases: dict,
) -> list[CodeAction]:
    undefined_names = parse_module(document.source, check_internal_scopes=True).undefined
    if not undefined_names:
        return [get_ca_remove_unnecessary_import(document, import_range)]

    externaly_defined = project.find_definitions(from_module, set(undefined_names))
    if not externaly_defined:
        return [get_ca_remove_unnecessary_import(document, import_range)]

    text_edits_from = get_edits_replace_module_w_from(from_module, externaly_defined, import_range)
    text_edits_module = get_edits_replace_from_w_module(
        document.source,
        from_module,
        {ImportedName(name) for name in externaly_defined},
        import_range,
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
    imported_modules: set[ImportedName],
    import_range: Range,
) -> list[CodeAction]:
    parsed = parse_module(document.source, check_internal_scopes=True, collect_imported_attrs=True)

    if len(imported_modules) != 1:
        # If there is a comma separated list, it probably must be splitted first
        # manually or with some other tool like Ruff
        return []

    module = imported_modules.pop()
    used_attrs = parsed.attr_usages.get(module.alias or module.name)
    if not used_attrs:
        return [get_ca_remove_unnecessary_import(document, import_range)]

    text_edits = get_edits_replace_module_w_from(module.name, used_attrs, import_range)

    for edit_range, new_value in strip_base_name(document.source, module.alias or module.name, used_attrs):
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
    document: Document, from_module: str, imported_names: set[ImportedName], import_range: Range, aliases: dict
) -> list[CodeAction]:
    text_edits = get_edits_replace_from_w_module(document.source, from_module, imported_names, import_range, aliases)
    return [
        CodeAction(
            title="Starkiller: Replace from import with module import",
            kind=CodeActionKind.SourceOrganizeImports,
            edit=WorkspaceEdit(changes={document.uri: text_edits}),
        )
    ]


def get_edits_replace_module_w_from(from_module: str, names: set[str], import_range: Range) -> list[TextEdit]:
    names_str = ", ".join(names)
    new_text = f"from {from_module} import {names_str}"
    return [TextEdit(range=import_range, new_text=new_text)]


def get_edits_replace_from_w_module(
    source: str,
    from_module: str,
    names: set[ImportedName],
    import_range: Range,
    aliases: dict[str, str],
) -> list[TextEdit]:
    new_text = f"import {from_module}"
    if from_module in aliases:
        alias = aliases[from_module]
        new_text += f" as {alias}"
    text_edits = [TextEdit(range=import_range, new_text=new_text)]

    rename_map = {n.alias or n.name: f"{from_module}.{n.name}" for n in names}
    for edit_range, new_value in rename(source, rename_map):
        rename_range = Range(
            start=Position(line=edit_range.start.line, character=edit_range.start.char),
            end=Position(line=edit_range.end.line, character=edit_range.end.char),
        )
        text_edits.append(TextEdit(range=rename_range, new_text=new_value))
    return text_edits


def get_ca_remove_unnecessary_import(document: Document, import_range: Range) -> CodeAction:
    import_line_num = import_range.start.line
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
