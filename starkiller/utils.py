"""Some stuff for internal use."""

import builtins
import inspect
import pathlib
import sys
import warnings

import jedi  # type: ignore

BUILTIN_FUNCTIONS = set(dir(builtins))
BUILTIN_MODULES = sys.builtin_module_names

JEDI_DIR = pathlib.Path(inspect.getfile(jedi)).resolve().parent
_stub_stdlib_dir = JEDI_DIR / "third_party/typeshed/stdlib"
if not _stub_stdlib_dir.is_dir():
    warnings.warn("Can't find stdlib stub files. Check Jedi installation.", RuntimeWarning, stacklevel=1)
    STUB_STDLIB_SUBDIRS = []
else:
    _stub_stdlib_dir, _stub_stdlib_subdirs, _stub_stdlib_files = next(_stub_stdlib_dir.walk())
    STUB_STDLIB_SUBDIRS = [_stub_stdlib_dir / sd for sd in _stub_stdlib_subdirs]
