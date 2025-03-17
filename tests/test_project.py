from starkiller.project import SKProject


def test_asyncio_definitions() -> None:
    project = SKProject(".")  # default project and env
    look_for = {"gather", "run", "TaskGroup"}
    names = project.get_definitions("asyncio", look_for)
    assert names == look_for
