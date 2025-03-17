# Starkiller

**Work in progress**

A wrapper around [Jedi](https://jedi.readthedocs.io/en/latest/index.html)'s `Project` that helps to analyse and refactor
imports in your Python code. Starkiller aims to be as static as possible, i.e. to analyse source code without actually
executing it.

The initial goal was to create a simple code formatter to get rid of star imports, hence the choice of the package name.

## Python LSP Server plugin

This package contains a plugin for [python-lsp-server](https://github.com/python-lsp/python-lsp-server) that provides
the following code actions to refactor import statements:

- `Replace * with explicit names` - suggested for `from ... import *` statements. 
- [wip] `Replace * import with module import` - suggested for `from ... import *` statements. 
- [wip] `Replace from import with module import` - suggested for `from ... import ...` statements.
- [wip] `Replace module import with from import` - suggested for `import ...` statements.

To enable the plugin install Starkiller in the same virtual environment as `python-lsp-server` with `[pylsp]` optional
dependency. E.g. with `pipx`: 

```bash
uv build
pipx inject python-lsp-server ./dist/starkiller-<VERSION>-py3-none-any.whl[pylsp]
```

The plugin is enabled just the same way as any other `pylsp` plugin. E.g., in Neovim via
[lspconfig](https://github.com/neovim/nvim-lspconfig):

```lua
require("lspconfig").pylsp.setup {
    settings = {
        pylsp = {
            plugins = {
                starkiller = {enabled = true},
            }
        }
    }
}
```

## Alternatives and inspiration

- [removestar](https://www.asmeurer.com/removestar/) provides a [Pyflakes](https://github.com/PyCQA/pyflakes) based
tool.
- [SurpriseDog's scripts](https://github.com/SurpriseDog/Star-Wrangler) are a great source of inspiration.
- `pylsp` itself has a built-in `rope_autoimport` plugin utilizing [Rope](https://github.com/python-rope/rope)'s
`autoimport` module.
