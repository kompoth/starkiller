"""Some stuff for internal use."""
import builtins
import sys

BUILTIN_FUNCTIONS = set(dir(builtins))
BUILTIN_MODULES = sys.builtin_module_names
