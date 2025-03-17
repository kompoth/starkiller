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

from starkiller.parsing import check_line_for_star_import, parse_module
from starkiller.project import SKProject

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
    active_range = converter.structure(range, Range)
    line = document.lines[active_range.start.line].rstrip("\r\n")
    edit_range = Range(
        start=Position(line=active_range.start.line, character=0),
        end=Position(line=active_range.start.line, character=len(line)),
    )
    code_actions: list[CodeAction] = []

    # Star import code actions
    from_module = check_line_for_star_import(line)
    if from_module:
        undefined_names = parse_module(document.source).undefined
        if undefined_names:
            project_path = pathlib.Path(workspace.root_path).resolve()
            env_path: pathlib.Path = project_path / ".venv"
            if env_path.exists():
                project = SKProject(project_path, environment_path=env_path)
            else:
                project = SKProject(project_path)

            definitions = project.get_definitions(from_module, undefined_names)
            if definitions:
                names_str = ", ".join(definitions)
                new_import_line = f"from {from_module} import {names_str}"
                text_edit = TextEdit(range=edit_range, new_text=new_import_line)
                workspace_edit = WorkspaceEdit(changes={document.uri: [text_edit]})
                code_actions.append(
                    CodeAction(
                        title="Starkiller: Replace * with imported names",
                        kind=CodeActionKind.SourceOrganizeImports,
                        edit=workspace_edit,
                    ),
                )

    return converter.unstructure(code_actions)
