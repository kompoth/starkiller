import pytest

from starkiller.parsing import ImportedName, ImportFromStatement, ImportModulesStatement, find_imports

TEST_CASE = """
from os import walk
from time import *
import sys as sys_module
from asyncio import (
    gather,
    run as arun,
)
import asyncio.taskgroup
import asyncio.taskgroup as tg_module
from asyncio.taskgroup import TaskGroup

if __name__ == "__main__":
    import asyncio
"""


@pytest.mark.parametrize(
    ("test_case", "row", "expected_from", "expected_names"),
    [
        pytest.param(TEST_CASE, 2, "os", [ImportedName("walk")]),
        pytest.param(TEST_CASE, 3, "time", None),
        pytest.param(TEST_CASE, 5, "asyncio", [ImportedName("gather"), ImportedName("run", "arun")]),
        pytest.param(TEST_CASE, 11, "asyncio.taskgroup", [ImportedName("TaskGroup")]),
    ],
)
def test_find_from_import(test_case: str, row: int, expected_from: str, expected_names: list[str] | None) -> None:
    found = find_imports(test_case, row)
    assert isinstance(found, ImportFromStatement)
    assert found.module == expected_from
    if expected_names is None:
        assert found.is_star
    else:
        assert found.names == set(expected_names)


@pytest.mark.parametrize(
    ("test_case", "row", "expected_modules"),
    [
        pytest.param(TEST_CASE, 4, [ImportedName("sys", "sys_module")]),
        pytest.param(TEST_CASE, 9, [ImportedName("asyncio.taskgroup")]),
        pytest.param(TEST_CASE, 10, [ImportedName("asyncio.taskgroup", "tg_module")]),
        pytest.param(TEST_CASE, 14, [ImportedName("asyncio")]),
    ],
)
def test_find_import(test_case: str, row: int, expected_modules: list[str]) -> None:
    found = find_imports(test_case, row)
    assert isinstance(found, ImportModulesStatement)
    assert found.modules == set(expected_modules)
