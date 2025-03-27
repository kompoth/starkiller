from pytest_virtualenv import VirtualEnv  # type: ignore

from starkiller.project import StarkillerProject


def test_asyncio_definitions() -> None:
    project = StarkillerProject(".")  # default project and env
    look_for = {"gather", "run", "TaskGroup"}
    names = project.find_definitions("asyncio", look_for)
    assert names == look_for


def test_numpy_definitions(virtualenv: VirtualEnv) -> None:
    virtualenv.install_package("numpy==2.2")
    project = StarkillerProject(virtualenv.workspace, env_path=virtualenv.virtualenv)

    find_in_numpy = {"ndarray", "apply_along_axis", "einsum", "linalg"}
    names = project.find_definitions("numpy", find_in_numpy)
    assert names == find_in_numpy

    find_in_numpy_linalg = {"norm", "eigvals", "cholesky"}
    names = project.find_definitions("numpy.linalg", find_in_numpy_linalg)
    assert names == find_in_numpy_linalg


def test_jedi_definitions(virtualenv: VirtualEnv) -> None:
    virtualenv.install_package("jedi==0.19.2")
    project = StarkillerProject(virtualenv.workspace, env_path=virtualenv.virtualenv)

    find_in_jedi = {"Project", "Script", "api"}
    names = project.find_definitions("jedi", find_in_jedi)
    assert names == find_in_jedi

    find_in_jedi_api = {"Script", "Project", "classes", "get_default_project", "project", "environment"}
    names = project.find_definitions("jedi.api", find_in_jedi_api)
    assert names == find_in_jedi_api

    find_in_jedi_api_project = {"Project", "get_default_project"}
    names = project.find_definitions("jedi.api", find_in_jedi_api_project)
    assert names == find_in_jedi_api_project
