# Starkiller

[![CI status](https://github.com/kompoth/starkiller/actions/workflows/ci.yaml/badge.svg)](https://github.com/kompoth/starkiller/actions)

**Work in progress**

A package and [python-lsp-server](https://github.com/python-lsp/python-lsp-server) plugin that helps to analyze and
refactor imports in your Python code.
Starkiller aims to be static, i.e. to analyse source code without actually executing it, and fast, thanks to built-in
`ast` module.

The initial goal was to create a simple linter to get rid of star imports, hence the choice of the package name.

## Python LSP Server plugin

The `pylsp` plugin provides the following code actions to refactor import statements:

- `Replace * with explicit names` - suggested for `from ... import *` statements. 
- `Replace * import with module import` - suggested for `from ... import *` statements. 
- [wip] `Replace from import with module import` - suggested for `from ... import ...` statements.
- [wip] `Replace module import with from import` - suggested for `import ...` statements.

To enable the plugin install Starkiller in the same virtual environment as `python-lsp-server` with `[pylsp]` optional
dependency. E.g., with `pipx`: 

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
                starkiller = { enabled = true },
                aliases = {
                    numpy = "np",
                    [ "matplotlib.pyplot" ] = "plt",
                }
            }
        }
    }
}
```

## Alternatives and inspiration

- [removestar](https://www.asmeurer.com/removestar/) is a [Pyflakes](https://github.com/PyCQA/pyflakes) based tool with
similar objectives.
- [SurpriseDog's scripts](https://github.com/SurpriseDog/Star-Wrangler) are a great source of inspiration.
- `pylsp` itself has a built-in `rope_autoimport` plugin utilizing [Rope](https://github.com/python-rope/rope)'s
`autoimport` module.
