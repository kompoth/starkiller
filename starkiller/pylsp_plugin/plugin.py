import dataclasses
import logging
import pathlib

from lsprotocol.converters import get_converter
from lsprotocol.types import (
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

from starkiller.parsing import find_from_import, find_import, parse_module
from starkiller.project import StarkillerProject
from starkiller.refactoring import get_rename_edits

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

    if from_module and imported_names and any(name.name == "*" for name in imported_names):
        # Star import statement code actions
        undefined_names = parse_module(document.source, check_internal_scopes=True).undefined
        if not undefined_names:
            # TODO: code action to remove import at all
            return []

        names_to_import = project.find_definitions(from_module, set(undefined_names))
        if not names_to_import:
            # TODO: code action to remove import at all
            return []

        code_actions.extend(
            [
                replace_star_with_names(document, from_module, names_to_import, line_range),
                replace_star_w_module(document, from_module, names_to_import, line_range, aliases),
            ],
        )
    elif from_module:
        # TODO: From import (without star) statement code actions
        pass
    elif imported_modules:
        # TODO: Import statement code actions
        pass

    return converter.unstructure(code_actions)


def replace_star_with_names(
    document: Document,
    from_module: str,
    names: set[str],
    import_line_range: Range,
) -> CodeAction:
    names_str = ", ".join(names)
    new_text = f"from {from_module} import {names_str}"
    text_edit = TextEdit(range=import_line_range, new_text=new_text)
    workspace_edit = WorkspaceEdit(changes={document.uri: [text_edit]})
    return CodeAction(
        title="Starkiller: Replace * with explicit names",
        kind=CodeActionKind.SourceOrganizeImports,
        edit=workspace_edit,
    )


def replace_star_w_module(
    document: Document,
    from_module: str,
    names: set[str],
    import_line_range: Range,
    aliases: dict[str, str],
) -> CodeAction:
    new_text = f"import {from_module}"
    if from_module in aliases:
        alias = aliases[from_module]
        new_text += f" as {alias}"
    text_edits = [TextEdit(range=import_line_range, new_text=new_text)]

    rename_map = {name: f"{from_module}.{name}" for name in names}
    for edit_range, new_value in get_rename_edits(document.source, rename_map):
        rename_range = Range(
            start=Position(line=edit_range.start.line, character=edit_range.start.char),
            end=Position(line=edit_range.end.line, character=edit_range.end.char),
        )
        text_edits.append(TextEdit(range=rename_range, new_text=new_value))

    workspace_edit = WorkspaceEdit(changes={document.uri: text_edits})
    return CodeAction(
        title="Starkiller: Replace * import with module import",
        kind=CodeActionKind.SourceOrganizeImports,
        edit=workspace_edit,
    )
