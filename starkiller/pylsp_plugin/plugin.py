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

log = logging.getLogger(__name__)
converter = get_converter()


@hookimpl
def pylsp_code_actions(
    config: Config,  # noqa: ARG001
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
        environment_path=env_path if env_path.exists() else None,
    )

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
        undefined_names = parse_module(document.source).undefined
        if not undefined_names:
            # TODO: code action to remove import at all
            return []

        names_to_import = project.get_definitions(from_module, set(undefined_names))
        if not names_to_import:
            return []

        code_actions.append(
            replace_star_with_names(document.uri, from_module, names_to_import, line_range)
            # TODO: code action to replace star with module
        )
    elif from_module:
        # TODO: From import (without star) statement code actions
        pass
    elif imported_modules:
        # TODO: Import statement code actions
        pass

    return converter.unstructure(code_actions)


def replace_star_with_names(
    file_uri: str,
    from_module: str,
    names: set[str],
    line_range: Range,
) -> CodeAction:
    names_str = ", ".join(names)
    new_text = f"from {from_module} import {names_str}"
    text_edit = TextEdit(range=line_range, new_text=new_text)
    workspace_edit = WorkspaceEdit(changes={file_uri: [text_edit]})
    return CodeAction(
        title="Starkiller: Replace * with explicit names",
        kind=CodeActionKind.SourceOrganizeImports,
        edit=workspace_edit,
    )
