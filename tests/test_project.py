from pytest_virtualenv import VirtualEnv  # type: ignore

from starkiller.project import StarkillerProject


def test_asyncio_definitions(virtualenv: VirtualEnv) -> None:
    project = StarkillerProject(virtualenv.workspace)
    find_in_asyncio = {"gather", "run", "TaskGroup"}
    names = project.find_definitions("asyncio", find_in_asyncio)
    assert names == find_in_asyncio

    find_in_asyncio_taskgroup = {"TaskGroup"}
    names = project.find_definitions("asyncio", find_in_asyncio_taskgroup)
    assert names == find_in_asyncio_taskgroup


def test_time_definitions(virtualenv: VirtualEnv) -> None:
    project = StarkillerProject(virtualenv.workspace)
    look_for = {"time", "sleep"}
    names = project.find_definitions("time", look_for)
    assert names == look_for


def test_fastapi_definitions(virtualenv: VirtualEnv) -> None:
    virtualenv.install_package("fastapi==0.115.12")
    project = StarkillerProject(virtualenv.workspace, env_path=virtualenv.virtualenv)

    find_in_fastapi = {"FastAPI", "Response", "status"}
    names = project.find_definitions("fastapi", find_in_fastapi)
    assert names == find_in_fastapi


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
