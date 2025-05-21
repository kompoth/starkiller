from starkiller.parsing import ImportedName, parse_module

TEST_CASE = """
import asyncio
import numpy as np
from jedi.api import *
from ABC import some_abc_method, abc as abc_alias
from lib.utils import use_proxy
from . import name_from_same_package
from .utils import some_db_handler

SOME_CONSTANT = "127.0.0.1"

@undefined_decorator
def some_function(arg1: int, arg2: abc_alias = undefined_default) -> tuple[name_from_same_package, int, int]:
    internal_scope_var = arg2 * arg1 * np.dot(12, 34)
    return internal_scope_var.lower(), 123, 456

print(internal_scope_var)
some_function_result, *some_ints = some_function(1998)

@use_proxy(proxies=undefined_list_of_proxies)
async def some_coroutine(data_model: UndefinedType) -> undefined_return_value | int:
    some_function()
    data_model = some_function_to_be_defined_later()
    return undefined_internal_scope_function(data_model) or data_model

class SomeClass(UndefinedClass):
    def __init__(self, init_arg):
        self.attr1 = init_arg
        self.attr2 = unknown_value_in_class_init

def some_function_to_be_defined_later():
    pass

if __name__ == "__main__":
    asyncio.run()
"""
EXPECTED_IMPORT_MAP = {
    "asyncio": {ImportedName(name="asyncio")},
    "numpy": {ImportedName(name="numpy", alias="np")},
    "jedi.api": {ImportedName(name="*")},
    "ABC": {
        ImportedName(name="some_abc_method"),
        ImportedName(name="abc", alias="abc_alias"),
    },
    "lib.utils": {ImportedName(name="use_proxy")},
    ".": {ImportedName(name="name_from_same_package")},
    ".utils": {ImportedName(name="some_db_handler")},
}
EXPECTED_DEFINED = {
    "some_function",
    "some_coroutine",
    "SOME_CONSTANT",
    "some_function_to_be_defined_later",
    "some_function_result",
    "some_ints",
    "SomeClass",
}
EXPECTED_UNDEFINED = {
    "undefined_decorator",
    "undefined_default",
    "UndefinedType",
    "internal_scope_var",
    "undefined_list_of_proxies",
    "undefined_return_value",
    "undefined_internal_scope_function",
    "UndefinedClass",
    "unknown_value_in_class_init",
}
EXPECTED_ATTRS = {
    "np": {"dot"},
    "asyncio": {"run"},
}


def test_parse_module() -> None:
    results = parse_module(TEST_CASE, check_internal_scopes=True)
    assert results.import_map == EXPECTED_IMPORT_MAP
    assert results.undefined == EXPECTED_UNDEFINED
    assert results.defined == EXPECTED_DEFINED


def test_find_definitions() -> None:
    look_for = {"some_coroutine", "SOME_CONSTANT", "there_is_no_such_name", "some_db_handler"}
    results = parse_module(TEST_CASE, find_definitions=look_for)
    assert results.defined == (look_for & EXPECTED_DEFINED)


def test_find_attrs() -> None:
    results = parse_module(TEST_CASE, check_internal_scopes=True, collect_imported_attrs=True)
    assert results.attr_usages == EXPECTED_ATTRS
