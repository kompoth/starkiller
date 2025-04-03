"""A class to work with imports in a Python project."""

import os
import pathlib
from importlib.machinery import ModuleSpec
from importlib.util import module_from_spec, spec_from_file_location
from types import ModuleType

# TODO: generate Jedi stub files
from jedi import create_environment, find_system_environments  # type: ignore

from starkiller.parsing import ImportedName, parse_module
from starkiller.utils import BUILTIN_FUNCTIONS


def _get_module_spec(module_name: str, paths: list[str]) -> ModuleSpec | None:
    file_candidates = {}
    dir_candidates = {}
    for path in paths:
        for dirpath, dirnames, filenames in os.walk(path):
            file_candidates[dirpath] = [fname for fname in filenames if fname.split(".")[0] == module_name]
            dir_candidates[dirpath] = [dname for dname in dirnames if dname == module_name]
            break

    for dirpath, fnames in file_candidates.items():
        for fname in fnames:
            spec = spec_from_file_location(fname.split(".")[0], dirpath + "/" + fname)
            if spec is not None:
                return spec

    for dirpath, dnames in dir_candidates.items():
        for dname in dnames:
            spec = spec_from_file_location(
                dname,
                dirpath + "/" + dname + "/__init__.py",
                submodule_search_locations=[dirpath + "/" + dname],
            )
            if spec is not None:
                return spec
    return None


class StarkillerProject:
    """Class to analyse imports in a Python project."""

    def __init__(self, project_path: pathlib.Path | str, env_path: pathlib.Path | str | None = None) -> None:
        """Inits project.

        Args:
            project_path: Path to the project root.
            env_path: Optional path to the project virtual environment.
        """
        self.path = pathlib.Path(project_path)
        if env_path:
            self.env = create_environment(path=env_path, safe=False)
        else:
            self.env = next(find_system_environments())

    def find_module(self, module_name: str) -> ModuleType | None:
        """Get module object by its name.

        Args:
            module_name: Full name of the module, e.g. `"jedi.api"`.

        Returns:
            Module object
        """
        lineage = module_name.split(".")

        prev_module_spec: ModuleSpec | None = None
        for lineage_module_name in lineage:
            prev_module_spec = self._find_module(lineage_module_name, prev_module_spec)

        if prev_module_spec is None:
            return None
        return module_from_spec(prev_module_spec)

    def _find_module(self, module_name: str, parent_spec: ModuleSpec | None) -> ModuleSpec | None:
        if parent_spec is None:
            env_sys_paths = self.env.get_sys_path()[::-1]
            paths = [self.path, *env_sys_paths]
        elif parent_spec.submodule_search_locations is None:
            return None
        else:
            paths = parent_spec.submodule_search_locations

        spec = _get_module_spec(module_name, paths)
        if spec is not None and parent_spec is not None:
            spec.name = parent_spec.name + "." + spec.name
        return spec

    def find_definitions(self, module_name: str, find_definitions: set[str]) -> set[str]:
        """Find definitions in module or package.

        Args:
            module_name: Full name of the module, e.g. "jedi.api".
            find_definitions: Set of definitions to look for.

        Returns:
            Set of found names
        """
        find_definitions -= BUILTIN_FUNCTIONS
        found_definitions: set[str]

        # Find the module location
        module = self.find_module(module_name)
        if module is None:
            return set()

        # Scan the module file for defintions
        module_path = pathlib.Path(str(module.__file__))
        with module_path.open() as module_file:
            names = parse_module(module_file.read(), find_definitions)
        found_definitions = names.defined

        # If package, its submodules should be importable
        if hasattr(module, "__path__"):
            found_definitions.update(self._find_submodules(module_name, find_definitions - found_definitions))

        # Follow imports
        for imod, inames in names.import_map.items():
            # Check what do we have left
            find_in_submod = find_definitions - found_definitions
            if not find_in_submod:
                return found_definitions

            found_definitions.update(self._find_definitions_follow_import(module_name, imod, inames, find_in_submod))

        return found_definitions

    def _find_submodules(self, module_name: str, find_submodules: set[str]) -> set[str]:
        found_submodules: set[str] = set()

        for name in find_submodules:
            possible_submodule_name = module_name + "." + name
            submodule = self.find_module(possible_submodule_name)
            if submodule:
                found_submodules.add(name)

        return found_submodules

    def _find_definitions_follow_import(
        self,
        module_name: str,
        imodule_name: str,
        inames: set[ImportedName],
        find_definitions: set[str]
    ) -> set[str]:
        module_short_name = module_name.split(".")[-1]
        found_definitions: set[str] = set()

        is_star = any(iname.name == "*" for iname in inames)
        is_relative_internal = imodule_name.startswith(".") and not imodule_name.startswith("..")
        is_internal = imodule_name.startswith((module_short_name, module_name)) or is_relative_internal
        if not is_internal:
            pass

        full_imodule_name = module_name + imodule_name if is_relative_internal else imodule_name

        if is_star:
            submodule_definitions = self.find_definitions(full_imodule_name, find_definitions)
            found_definitions.update(submodule_definitions)
        else:
            imported_from_submodule = {iname.name for iname in inames}
            found_definitions.update(imported_from_submodule & find_definitions)

        return found_definitions
