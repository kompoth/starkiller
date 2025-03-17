"""A class to work with imports in a Python project."""

import os
import pathlib
from importlib.machinery import ModuleSpec
from importlib.util import module_from_spec, spec_from_file_location
from types import ModuleType

from jedi import Project  # type: ignore

from starkiller.parsing import ModuleNames, parse_module


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


class SKProject(Project):
    """Wraps `jedi.Project` enabling import refactoring features."""

    def find_module(self, module_name: str) -> ModuleType | None:
        """Get module object by its name.

        Args:
            module_name: Full name of the module, e.g. `"jedi.api"`

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
            env = self.get_environment()
            env_sys_paths = env.get_sys_path()[::-1]
            paths = [self.path, *env_sys_paths]
        elif parent_spec.submodule_search_locations is None:
            return None
        else:
            paths = parent_spec.submodule_search_locations

        spec = _get_module_spec(module_name, paths)
        if spec is not None and parent_spec is not None:
            spec.name = parent_spec.name + "." + spec.name
        return spec

    def get_names_from_module(self, module_name: str, find_definitions: set[str] | None = None) -> ModuleNames | None:
        """Finds names from given module. Mostly for internal use.

        Args:
            module_name: Full name of the module, e.g. "jedi.api"
            find_definitions: Optional set of definitions to look for

        Returns:
            ModuleNames object
        """
        module = self.find_module(module_name)
        if module is None:
            return None

        module_path = pathlib.Path(str(module.__file__))
        with module_path.open() as module_file:
            return parse_module(module_file.read(), find_definitions)

    def get_definitions(
        self,
        module_name: str,
        find_definitions: set[str] | None = None,
    ) -> set[str]:
        """Find definitions from given module.

        Args:
            module_name: Full name of the module, e.g. "jedi.api"
            find_definitions: Optional set of definitions to look for

        Returns:
            Set of definitions
        """
        module_short_name = module_name.split(".")[-1]

        module = self.find_module(module_name)
        if module is None:
            return set()

        module_path = pathlib.Path(str(module.__file__))
        with module_path.open() as module_file:
            names = parse_module(module_file.read(), find_definitions)
        if not names:
            return set()
        definitions = names.defined

        if not hasattr(module, "__path__"):
            # This is not a package
            return definitions

        stars = []
        for imod, inames in names.import_map.items():
            is_star = any(iname.name == "*" for iname in inames)
            is_this_package = imod.startswith(".") and not imod.startswith("..")
            is_internal = imod.startswith(module_short_name) or is_this_package
            if is_star and is_internal:
                if is_this_package:
                    stars.append(module_name + imod)
                else:
                    stars.append(imod)

        for star in stars:
            star_definitions = self.get_definitions(star, find_definitions)
            definitions.update(star_definitions)

        return definitions
