"""A class to work with imports in a Python project."""

from importlib.util import spec_from_file_location
from pathlib import Path

# TODO: generate Jedi stub files
from jedi import create_environment, find_system_environments  # type: ignore

from starkiller.models import ImportedName, Module
from starkiller.parsing import parse_module
from starkiller.utils import BUILTIN_FUNCTIONS, BUILTIN_MODULES, STUB_STDLIB_SUBDIRS

MODULE_EXTENSIONS = (".py", ".pyi")


def _search_for_module(module_name: str, paths: list[Path]) -> Module | None:
    file_candidates = []
    dir_candidates = []
    for path in paths:
        for _, dirnames, filenames in path.walk():
            filepaths = [Path(path / n) for n in filenames]
            file_candidates.extend([
                file for file in filepaths if (file.stem == module_name) and (file.suffix in MODULE_EXTENSIONS)
            ])
            dir_candidates.extend([path / dname for dname in dirnames if dname == module_name])
            break

    for file in file_candidates:
        return Module(name=file.stem, fullname=file.stem, path=file)

    for directory in dir_candidates:
        init_path = directory / "__init__.py"
        spec = spec_from_file_location(directory.stem, init_path, submodule_search_locations=[str(directory)])
        if spec is not None:
            return Module(name=directory.name, fullname=spec.name, path=init_path, submodule_paths=[directory])

    return None


class StarkillerProject:
    """Class to analyse imports in a Python project."""

    def __init__(self, project_path: Path | str, env_path: Path | str | None = None) -> None:
        """Inits project.

        Args:
            project_path: Path to the project root.
            env_path: Optional path to the project virtual environment.
        """
        self.path = Path(project_path)
        if env_path:
            self.env = create_environment(path=env_path, safe=False)
        else:
            self.env = next(find_system_environments())

    def find_module(self, module_name: str) -> Module | None:
        """Get module object by its name.

        Args:
            module_name: Full name of the module, e.g. `"jedi.api"`.

        Returns:
            Module object
        """
        lineage = module_name.split(".")

        prev_module: Module | None = None
        for lineage_module_name in lineage:
            prev_module = self._find_module(lineage_module_name, prev_module)

        return prev_module

    def _find_module(self, module_name: str, parent_module: Module | None) -> Module | None:
        if parent_module is None:
            env_sys_paths = [Path(p) for p in self.env.get_sys_path()[::-1]]
            paths = [self.path, *env_sys_paths]
        elif parent_module.submodule_paths is None:
            return None
        else:
            paths = parent_module.submodule_paths

        if module_name in BUILTIN_MODULES:
            paths.extend(STUB_STDLIB_SUBDIRS)

        module = _search_for_module(module_name, paths)
        if module is not None and parent_module is not None:
            module.fullname = parent_module.fullname + "." + module.name
        return module

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
        with module.path.open() as module_file:
            names = parse_module(module_file.read(), find_definitions)
        found_definitions = names.defined

        # If package, its submodules should be importable
        if module.package:
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
