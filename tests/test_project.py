import pathlib
import subprocess  # noqa: S404
import sys
import venv
from collections.abc import Generator
from dataclasses import dataclass
from tempfile import TemporaryDirectory

import pytest

from starkiller.project import StarkillerProject


@dataclass
class SampleProject:
    project_path: pathlib.Path
    env_path: pathlib.Path


@pytest.fixture
def sample_project() -> Generator[SampleProject]:
    with TemporaryDirectory() as tmpdirpath:
        project_path = pathlib.Path(tmpdirpath).resolve()
        env_path = project_path / "venv"
        venv.create(env_path, with_pip=True)
        yield SampleProject(project_path, env_path)


def install_packages(project: SampleProject, packages: list[str]) -> None:
    python_path = project.env_path / ("Scripts" if sys.platform == "win32" else "bin") / "python"
    subprocess.check_call([python_path, "-m", "pip", "install", *packages])  # noqa: S603


def test_asyncio_definitions() -> None:
    project = StarkillerProject(".")  # default project and env
    look_for = {"gather", "run", "TaskGroup"}
    names = project.find_definitions("asyncio", look_for)
    assert names == look_for


def test_numpy_definitions(sample_project: SampleProject) -> None:
    install_packages(sample_project, ["numpy==2.2"])
    project = StarkillerProject(sample_project.project_path, environment_path=sample_project.env_path)

    find_in_numpy = {"ndarray", "apply_along_axis", "einsum", "linalg"}
    names = project.find_definitions("numpy", find_in_numpy)
    assert names == find_in_numpy

    find_in_numpy_linalg = {"norm", "eigvals", "cholesky"}
    names = project.find_definitions("numpy.linalg", find_in_numpy_linalg)
    assert names == find_in_numpy_linalg


def test_jedi_definitions(sample_project: SampleProject) -> None:
    install_packages(sample_project, ["jedi==0.19.2"])
    project = StarkillerProject(sample_project.project_path, environment_path=sample_project.env_path)

    find_in_jedi = {"Project", "Script", "api"}
    names = project.find_definitions("jedi", find_in_jedi)
    assert names == find_in_jedi

    find_in_jedi_api = {"Script", "Project", "classes", "get_default_project", "project", "environment"}
    names = project.find_definitions("jedi.api", find_in_jedi_api)
    assert names == find_in_jedi_api

    find_in_jedi_api_project = {"Project", "get_default_project"}
    names = project.find_definitions("jedi.api", find_in_jedi_api_project)
    assert names == find_in_jedi_api_project
