from starkiller.project import StarkillerProject


def test_asyncio_definitions() -> None:
    project = StarkillerProject(".")  # default project and env
    look_for = {"gather", "run", "TaskGroup"}
    names = project.get_definitions("asyncio", look_for)
    assert names == look_for
