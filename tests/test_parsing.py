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

if __name__ == "__main__":
    import asyncio
"""


@pytest.mark.parametrize(
    ("test_case", "row", "expected"),
    [
        pytest.param(TEST_CASE, 2, ImportFromStatement(module="os", names={ImportedName("walk")})),
        pytest.param(TEST_CASE, 3, ImportFromStatement(module="time", is_star=True)),
        pytest.param(TEST_CASE, 4, ImportModulesStatement(modules={ImportedName("sys", "sys_module")})),
        pytest.param(
            TEST_CASE,
            5,
            ImportFromStatement(module="asyncio", names={ImportedName("gather"), ImportedName("run", "arun")}),
        ),
        pytest.param(TEST_CASE, 9, ImportModulesStatement(modules={ImportedName("asyncio.taskgroup")})),
        pytest.param(TEST_CASE, 10, ImportModulesStatement(modules={ImportedName("asyncio.taskgroup", "tg_module")})),
    ],
)
def test_find_from_import(test_case: str, row: int, expected: ImportFromStatement | ImportModulesStatement) -> None:
    assert find_imports(test_case, row) == expected
